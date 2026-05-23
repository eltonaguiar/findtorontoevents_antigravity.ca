-- Trade log for VWAP_ELITE_v1
-- Generated: 2026-03-08T18:36:22.511502
-- Total trades: 892


INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '42FBB434889BD22F', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-01-03 07:00:00', '2020-01-03 15:04:05', 4536.46389527, 4554.94193499,
    4468.41693684, 4649.87549265, 0.0866,
    0.4073, 3.53, 'TIME_EXIT', 8.07,
    1, '1h', '2026-03-08T18:36:22.482114'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4073,
    pnl_amount = 3.53,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '720E0AD23DBA5B49', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-01-03 12:00:00', '2020-01-03 14:58:02', 838.22803658, 841.92907277,
    825.65461603, 859.1837375, 0.085,
    0.4415, 3.75, 'TRAILING_STOP', 2.97,
    1, '1h', '2026-03-08T18:36:22.483275'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4415,
    pnl_amount = 3.75,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9EFA679A4E91F675', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-01-03 15:00:00', '2020-01-04 01:34:50', 1756.42666903, 1762.95904883,
    1730.080269, 1800.33733576, 0.0823,
    0.3719, 3.06, 'TIME_EXIT', 10.58,
    1, '1h', '2026-03-08T18:36:22.480306'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3719,
    pnl_amount = 3.06,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C47E009C4F78AF5', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-01-06 06:00:00', '2020-01-06 11:44:50', 4074.30621675, 4091.10006038,
    4013.19162349, 4176.16387216, 0.0938,
    0.4122, 3.87, 'TRAILING_STOP', 5.75,
    1, '1h', '2026-03-08T18:36:22.480315'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4122,
    pnl_amount = 3.87,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '409B3A001A5203E4', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-01-07 02:00:00', '2020-01-07 12:52:54', 3108.78082093, 3125.41102456,
    3062.14910861, 3186.50034145, 0.1086,
    0.5349, 5.81, 'TIME_EXIT', 10.88,
    1, '1h', '2026-03-08T18:36:22.479221'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5349,
    pnl_amount = 5.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0344B9A7E9F138EC', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-01-07 16:00:00', '2020-01-07 18:01:42', 2713.79023451, 2728.76148936,
    2673.08338099, 2781.63499037, 0.1019,
    0.5517, 5.62, 'TAKE_PROFIT', 2.03,
    1, '1h', '2026-03-08T18:36:22.479168'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5517,
    pnl_amount = 5.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A60B364293810C03', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2020-01-08 01:00:00', '2020-01-08 04:28:23', 2617.32924156, 2629.85168784,
    2578.06930294, 2682.7624726, 0.0941,
    0.4784, 4.5, 'TRAILING_STOP', 3.47,
    1, '1h', '2026-03-08T18:36:22.482646'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4784,
    pnl_amount = 4.5,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '667692763E0C7451', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-01-11 20:00:00', '2020-01-12 06:23:56', 3592.87859354, 3579.45280431,
    3538.98541464, 3682.70055838, 0.0977,
    -0.3737, -3.65, 'STOP_LOSS', 10.4,
    0, '1h', '2026-03-08T18:36:22.477671'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3737,
    pnl_amount = -3.65,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6693717E0D61EFF1', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-01-15 19:00:00', '2020-01-16 02:11:27', 37272.84205344, 37021.47145397,
    37831.93468424, 36341.0210021, 0.1049,
    0.6744, 7.07, 'TIME_EXIT', 7.19,
    1, '1h', '2026-03-08T18:36:22.483144'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6744,
    pnl_amount = 7.07,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BA7F8C34EEB9922B', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-01-17 05:00:00', '2020-01-17 16:33:45', 3172.68735883, 3194.22257954,
    3125.09704844, 3252.0045428, 0.0924,
    0.6788, 6.27, 'TAKE_PROFIT', 11.56,
    1, '1h', '2026-03-08T18:36:22.477748'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6788,
    pnl_amount = 6.27,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2D84244314DF4A4C', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-01-18 19:00:00', '2020-01-18 22:07:01', 3088.22664973, 3068.38583686,
    3134.55004948, 3011.02098349, 0.1003,
    0.6425, 6.44, 'TAKE_PROFIT', 3.12,
    1, '1h', '2026-03-08T18:36:22.481758'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6425,
    pnl_amount = 6.44,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '52BB6F564140DB97', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-01-19 08:00:00', '2020-01-19 11:34:18', 2038.42182992, 2047.81263614,
    2007.84550247, 2089.38237566, 0.1157,
    0.4607, 5.33, 'TRAILING_STOP', 3.57,
    1, '1h', '2026-03-08T18:36:22.475924'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4607,
    pnl_amount = 5.33,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '026EF058B5898685', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-01-19 10:00:00', '2020-01-19 16:31:41', 4028.90872547, 4043.69937249,
    3968.47509459, 4129.63144361, 0.1191,
    0.3671, 4.37, 'TAKE_PROFIT', 6.53,
    1, '1h', '2026-03-08T18:36:22.477699'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3671,
    pnl_amount = 4.37,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7BA9FB2DD6B19A39', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-01-19 11:00:00', '2020-01-19 19:50:53', 2072.49988352, 2083.5633592,
    2041.41238527, 2124.31238061, 0.1144,
    0.5338, 6.11, 'TAKE_PROFIT', 8.85,
    1, '1h', '2026-03-08T18:36:22.476470'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5338,
    pnl_amount = 6.11,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '91610B2A0DC37B50', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-01-19 23:00:00', '2020-01-20 10:03:31', 24236.94858886, 24382.8549041,
    23873.39436002, 24842.87230358, 0.1086,
    0.602, 6.53, 'TAKE_PROFIT', 11.06,
    1, '1h', '2026-03-08T18:36:22.477461'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.602,
    pnl_amount = 6.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FF465BBEF8C606D2', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-01-20 20:00:00', '2020-01-21 01:57:35', 2994.16214027, 2975.17570038,
    3039.07457237, 2919.30808676, 0.1006,
    0.6341, 6.38, 'TRAILING_STOP', 5.96,
    1, '1h', '2026-03-08T18:36:22.479576'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6341,
    pnl_amount = 6.38,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D746FE057526DAC6', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2020-01-26 07:00:00', '2020-01-26 12:48:21', 4516.06899887, 4484.99411769,
    4583.81003385, 4403.16727389, 0.0896,
    0.6881, 6.17, 'TRAILING_STOP', 5.81,
    1, '1h', '2026-03-08T18:36:22.481912'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6881,
    pnl_amount = 6.17,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7A83CF5A02F913AE', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-01-27 14:00:00', '2020-01-27 23:28:20', 3382.45991278, 3365.92184214,
    3433.19681147, 3297.89841496, 0.0926,
    0.4889, 4.53, 'TAKE_PROFIT', 9.47,
    1, '1h', '2026-03-08T18:36:22.483266'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4889,
    pnl_amount = 4.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '07CA3798A513BDA7', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-01-28 03:00:00', '2020-01-28 07:26:47', 2720.57553927, 2732.87717281,
    2679.76690618, 2788.58992775, 0.09,
    0.4522, 4.07, 'TRAILING_STOP', 4.45,
    1, '1h', '2026-03-08T18:36:22.476155'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4522,
    pnl_amount = 4.07,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1BB1E9D30BCD3E0C', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-01-28 03:00:00', '2020-01-28 07:28:36', 3510.63591063, 3486.23800483,
    3563.29544929, 3422.87001286, 0.0892,
    0.695, 6.2, 'TIME_EXIT', 4.48,
    1, '1h', '2026-03-08T18:36:22.476507'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.695,
    pnl_amount = 6.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2CF9C8203C663BE4', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2020-01-28 20:00:00', '2020-01-29 02:27:47', 4537.69816532, 4511.50829712,
    4605.7636378, 4424.25571119, 0.0945,
    0.5772, 5.45, 'TIME_EXIT', 6.46,
    1, '1h', '2026-03-08T18:36:22.477794'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5772,
    pnl_amount = 5.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8079ADC706BE73FA', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-01-31 16:00:00', '2020-02-01 00:59:15', 24020.95892629, 24164.99834598,
    23660.6445424, 24621.48289945, 0.0919,
    0.5996, 5.51, 'TIME_EXIT', 8.99,
    1, '1h', '2026-03-08T18:36:22.479357'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5996,
    pnl_amount = 5.51,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9F2E8FBA8110DE7E', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-02-04 05:00:00', '2020-02-04 12:49:48', 11805.52748123, 11859.06401176,
    11628.44456901, 12100.66566826, 0.1128,
    0.4535, 5.12, 'TIME_EXIT', 7.83,
    1, '1h', '2026-03-08T18:36:22.481730'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4535,
    pnl_amount = 5.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5022BD603615B93E', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-02-06 17:00:00', '2020-02-07 02:54:44', 312.20185595, 313.04671884,
    316.88488379, 304.39680955, 0.1041,
    -0.2706, -2.82, 'TIME_EXIT', 9.91,
    0, '1h', '2026-03-08T18:36:22.482448'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2706,
    pnl_amount = -2.82,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3105A050635137F1', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-02-08 12:00:00', '2020-02-08 17:19:50', 391.59739346, 393.55446988,
    385.72343256, 401.3873283, 0.0946,
    0.4998, 4.73, 'TAKE_PROFIT', 5.33,
    1, '1h', '2026-03-08T18:36:22.483040'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4998,
    pnl_amount = 4.73,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F6C29A09D2511E5B', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-02-09 09:00:00', '2020-02-09 20:43:17', 3534.73228556, 3544.31745079,
    3587.75326984, 3446.36397842, 0.1114,
    -0.2712, -3.02, 'STOP_LOSS', 11.72,
    0, '1h', '2026-03-08T18:36:22.478194'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2712,
    pnl_amount = -3.02,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E884347D2F50B32C', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-02-16 06:00:00', '2020-02-16 09:55:53', 17303.97456341, 17423.16400649,
    17044.41494496, 17736.57392749, 0.0875,
    0.6888, 6.03, 'TAKE_PROFIT', 3.93,
    1, '1h', '2026-03-08T18:36:22.475982'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6888,
    pnl_amount = 6.03,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BD15C3B3878F09AA', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-02-23 21:00:00', '2020-02-23 23:30:36', 4712.78875094, 4736.16880847,
    4642.09691967, 4830.60846971, 0.0931,
    0.4961, 4.62, 'TRAILING_STOP', 2.51,
    1, '1h', '2026-03-08T18:36:22.477120'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4961,
    pnl_amount = 4.62,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '03E42806A76ACB40', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-02-26 18:00:00', '2020-02-26 20:27:36', 3938.64376699, 3919.68712467,
    3997.72342349, 3840.17767281, 0.1053,
    0.4813, 5.07, 'TIME_EXIT', 2.46,
    1, '1h', '2026-03-08T18:36:22.480177'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4813,
    pnl_amount = 5.07,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '57EBFD42AC37F27C', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-02-27 06:00:00', '2020-02-27 09:20:50', 4229.19881138, 4251.6809515,
    4165.7608292, 4334.92878166, 0.106,
    0.5316, 5.64, 'TRAILING_STOP', 3.35,
    1, '1h', '2026-03-08T18:36:22.483755'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5316,
    pnl_amount = 5.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F64FCE5CF9D2AC52', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-03-02 00:00:00', '2020-03-02 10:04:41', 1181.24671984, 1174.85756509,
    1198.96542063, 1151.71555184, 0.0921,
    0.5409, 4.98, 'TRAILING_STOP', 10.08,
    1, '1h', '2026-03-08T18:36:22.476810'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5409,
    pnl_amount = 4.98,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0C6184418093149A', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-03-08 23:00:00', '2020-03-09 10:57:32', 2797.29880124, 2809.47751498,
    2755.33931922, 2867.23127127, 0.1113,
    0.4354, 4.85, 'TAKE_PROFIT', 11.96,
    1, '1h', '2026-03-08T18:36:22.476210'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4354,
    pnl_amount = 4.85,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '594248684E1E6370', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-03-09 20:00:00', '2020-03-09 23:56:07', 4671.31658544, 4657.65140292,
    4601.24683666, 4788.09950008, 0.1016,
    -0.2925, -2.97, 'TIME_EXIT', 3.94,
    0, '1h', '2026-03-08T18:36:22.482655'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2925,
    pnl_amount = -2.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F8665B61DE940A47', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-03-10 05:00:00', '2020-03-10 15:25:54', 44863.14389461, 44703.40306541,
    45536.09105303, 43741.56529725, 0.1175,
    0.3561, 4.18, 'TAKE_PROFIT', 10.43,
    1, '1h', '2026-03-08T18:36:22.478539'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3561,
    pnl_amount = 4.18,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B36CE4F7305ED739', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-03-11 03:00:00', '2020-03-11 08:00:52', 44278.00332042, 44032.82951627,
    44942.17337022, 43171.05323741, 0.0891,
    0.5537, 4.93, 'TRAILING_STOP', 5.01,
    1, '1h', '2026-03-08T18:36:22.480560'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5537,
    pnl_amount = 4.93,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EB8F58BF25CB3EF7', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-03-12 14:00:00', '2020-03-12 20:06:43', 3806.82992527, 3793.4074486,
    3749.72747639, 3902.0006734, 0.1001,
    -0.3526, -3.53, 'STOP_LOSS', 6.11,
    0, '1h', '2026-03-08T18:36:22.475915'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3526,
    pnl_amount = -3.53,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9EF8869421B1947A', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2020-03-12 14:00:00', '2020-03-12 17:44:01', 371.34484083, 369.2773533,
    376.91501344, 362.06121981, 0.1121,
    0.5568, 6.24, 'TAKE_PROFIT', 3.73,
    1, '1h', '2026-03-08T18:36:22.481313'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5568,
    pnl_amount = 6.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '00F91FDB09BBA41A', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-03-13 03:00:00', '2020-03-13 12:23:02', 857.50421591, 854.77624551,
    844.64165267, 878.9418213, 0.1138,
    -0.3181, -3.62, 'TIME_EXIT', 9.38,
    0, '1h', '2026-03-08T18:36:22.480722'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3181,
    pnl_amount = -3.62,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1BB30984508FC3AE', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-03-14 22:00:00', '2020-03-15 01:54:29', 1421.23350635, 1427.14624058,
    1399.91500376, 1456.76434401, 0.1193,
    0.416, 4.96, 'TAKE_PROFIT', 3.91,
    1, '1h', '2026-03-08T18:36:22.478336'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.416,
    pnl_amount = 4.96,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CC5617085F571DEC', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-03-16 00:00:00', '2020-03-16 07:02:44', 1823.95439714, 1811.54346489,
    1851.3137131, 1778.35553721, 0.0928,
    0.6804, 6.31, 'TAKE_PROFIT', 7.05,
    1, '1h', '2026-03-08T18:36:22.479870'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6804,
    pnl_amount = 6.31,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EC3473F8FB893C02', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2020-03-16 13:00:00', '2020-03-16 16:03:45', 516.63408277, 520.22352034,
    508.88457153, 529.54993484, 0.0834,
    0.6948, 5.79, 'TAKE_PROFIT', 3.06,
    1, '1h', '2026-03-08T18:36:22.481950'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6948,
    pnl_amount = 5.79,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '92D8F6AD3CF5EA5B', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-03-19 18:00:00', '2020-03-20 00:11:50', 4030.05359445, 4011.39677396,
    4090.50439836, 3929.30225459, 0.1062,
    0.4629, 4.92, 'TRAILING_STOP', 6.2,
    1, '1h', '2026-03-08T18:36:22.480761'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4629,
    pnl_amount = 4.92,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E41554C3B59B4E7B', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-03-25 22:00:00', '2020-03-26 02:39:59', 1118.57565757, 1115.2737299,
    1101.7970227, 1146.54004901, 0.1111,
    -0.2952, -3.28, 'STOP_LOSS', 4.67,
    0, '1h', '2026-03-08T18:36:22.482892'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2952,
    pnl_amount = -3.28,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '922196679F5C36BC', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-03-26 05:00:00', '2020-03-26 16:23:39', 4009.38765377, 3995.15741994,
    3949.24683896, 4109.62234511, 0.0879,
    -0.3549, -3.12, 'STOP_LOSS', 11.39,
    0, '1h', '2026-03-08T18:36:22.477311'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3549,
    pnl_amount = -3.12,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FAF3D24D0909B7F1', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-03-26 09:00:00', '2020-03-26 12:36:01', 4226.53869515, 4247.25086893,
    4163.14061472, 4332.20216253, 0.1135,
    0.4901, 5.56, 'TRAILING_STOP', 3.6,
    1, '1h', '2026-03-08T18:36:22.476603'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4901,
    pnl_amount = 5.56,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '354AF73DB990AF87', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-03-27 21:00:00', '2020-03-28 02:33:53', 3271.24630727, 3287.7674885,
    3222.17761266, 3353.02746495, 0.0987,
    0.505, 4.99, 'TIME_EXIT', 5.56,
    1, '1h', '2026-03-08T18:36:22.476089'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.505,
    pnl_amount = 4.99,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8411D78A4494C925', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-03-28 22:00:00', '2020-03-29 07:30:58', 4259.012375, 4284.40104747,
    4195.12718938, 4365.48768438, 0.1195,
    0.5961, 7.12, 'TIME_EXIT', 9.52,
    1, '1h', '2026-03-08T18:36:22.476975'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5961,
    pnl_amount = 7.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '655D72C8D3E91AB5', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-03-31 12:00:00', '2020-03-31 23:09:09', 43753.21067438, 43561.7218019,
    44409.50883449, 42659.38040752, 0.1007,
    0.4377, 4.41, 'TRAILING_STOP', 11.15,
    1, '1h', '2026-03-08T18:36:22.479558'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4377,
    pnl_amount = 4.41,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '664AAC1BA99B0B07', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-04-01 20:00:00', '2020-04-02 01:53:49', 875.43039769, 879.83829721,
    862.29894173, 897.31615764, 0.1155,
    0.5035, 5.82, 'TRAILING_STOP', 5.9,
    1, '1h', '2026-03-08T18:36:22.483599'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5035,
    pnl_amount = 5.82,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B39DE38846249B00', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-04-01 22:00:00', '2020-04-02 08:06:01', 2927.26977648, 2919.5875809,
    2883.36072983, 3000.45152089, 0.1187,
    -0.2624, -3.11, 'TIME_EXIT', 10.1,
    0, '1h', '2026-03-08T18:36:22.479529'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2624,
    pnl_amount = -3.11,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '970E7DC63CFA6F40', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2020-04-07 01:00:00', '2020-04-07 07:47:59', 1101.44921971, 1094.4876011,
    1117.970958, 1073.91298921, 0.0875,
    0.632, 5.53, 'TAKE_PROFIT', 6.8,
    1, '1h', '2026-03-08T18:36:22.480279'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.632,
    pnl_amount = 5.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6AC81C0302338EFA', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-04-09 12:00:00', '2020-04-09 21:27:15', 1518.35364186, 1512.22647468,
    1541.12894649, 1480.39480082, 0.1166,
    0.4035, 4.7, 'TRAILING_STOP', 9.45,
    1, '1h', '2026-03-08T18:36:22.483412'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4035,
    pnl_amount = 4.7,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '12EDFCB9881F261E', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-04-09 13:00:00', '2020-04-09 15:12:11', 3591.92165495, 3601.36055472,
    3645.80047978, 3502.12361358, 0.0907,
    -0.2628, -2.38, 'TIME_EXIT', 2.2,
    0, '1h', '2026-03-08T18:36:22.484041'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2628,
    pnl_amount = -2.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3708BAC5D96FCAC0', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-04-11 22:00:00', '2020-04-12 00:08:03', 21164.51285138, 21039.70607953,
    21481.98054415, 20635.40003009, 0.0972,
    0.5897, 5.73, 'TAKE_PROFIT', 2.13,
    1, '1h', '2026-03-08T18:36:22.476539'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5897,
    pnl_amount = 5.73,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1414CE4DC8AA9D26', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2020-04-12 01:00:00', '2020-04-12 10:47:06', 3376.61925311, 3363.7777226,
    3427.2685419, 3292.20377178, 0.1106,
    0.3803, 4.21, 'TRAILING_STOP', 9.79,
    1, '1h', '2026-03-08T18:36:22.482574'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3803,
    pnl_amount = 4.21,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C6945B502F4695A9', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-04-12 19:00:00', '2020-04-12 21:50:22', 3603.4533129, 3593.26091851,
    3549.4015132, 3693.53964572, 0.0877,
    -0.2829, -2.48, 'STOP_LOSS', 2.84,
    0, '1h', '2026-03-08T18:36:22.477758'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2829,
    pnl_amount = -2.48,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1C98A4422C58314D', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-04-18 23:00:00', '2020-04-19 07:36:01', 3212.43168989, 3200.97581323,
    3164.24521454, 3292.74248214, 0.1144,
    -0.3566, -4.08, 'TIME_EXIT', 8.6,
    0, '1h', '2026-03-08T18:36:22.478935'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3566,
    pnl_amount = -4.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '70A9624AF4A99E00', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-04-18 23:00:00', '2020-04-19 07:54:01', 36407.90081484, 36289.47962294,
    35861.78230262, 37318.09833521, 0.0884,
    -0.3253, -2.87, 'TIME_EXIT', 8.9,
    0, '1h', '2026-03-08T18:36:22.479907'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3253,
    pnl_amount = -2.87,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3773225492F539FA', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-04-19 12:00:00', '2020-04-19 17:44:40', 3113.28742503, 3125.80407753,
    3066.58811366, 3191.11961066, 0.0936,
    0.402, 3.76, 'TRAILING_STOP', 5.74,
    1, '1h', '2026-03-08T18:36:22.481221'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.402,
    pnl_amount = 3.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4011DEEE25C2D21A', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-04-20 01:00:00', '2020-04-20 11:45:03', 2379.34475079, 2370.33901235,
    2343.65457952, 2438.82836956, 0.0875,
    -0.3785, -3.31, 'STOP_LOSS', 10.75,
    0, '1h', '2026-03-08T18:36:22.477848'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3785,
    pnl_amount = -3.31,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4996202C01015F69', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-04-21 12:00:00', '2020-04-21 16:06:31', 185.48001259, 186.19578974,
    182.6978124, 190.1170129, 0.0979,
    0.3859, 3.78, 'TRAILING_STOP', 4.11,
    1, '1h', '2026-03-08T18:36:22.479009'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3859,
    pnl_amount = 3.78,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F53362C91DC91EE8', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-04-22 05:00:00', '2020-04-22 15:00:14', 1549.40929106, 1543.53832946,
    1572.65043043, 1510.67405878, 0.1081,
    0.3789, 4.1, 'TRAILING_STOP', 10.0,
    1, '1h', '2026-03-08T18:36:22.477364'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3789,
    pnl_amount = 4.1,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C4EAFA9D88090CA3', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-04-22 05:00:00', '2020-04-22 07:56:35', 637.14311368, 635.10680086,
    627.58596697, 653.07169152, 0.0963,
    -0.3196, -3.08, 'STOP_LOSS', 2.94,
    0, '1h', '2026-03-08T18:36:22.480605'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3196,
    pnl_amount = -3.08,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B06F32E5CBF91896', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-04-27 19:00:00', '2020-04-28 01:19:37', 633.38425336, 631.62023017,
    623.88348956, 649.2188597, 0.101,
    -0.2785, -2.81, 'STOP_LOSS', 6.33,
    0, '1h', '2026-03-08T18:36:22.480333'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2785,
    pnl_amount = -2.81,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '682BEB274953C67E', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2020-05-01 00:00:00', '2020-05-01 05:12:07', 2164.61903666, 2156.69444163,
    2197.08832221, 2110.50356074, 0.1068,
    0.3661, 3.91, 'TRAILING_STOP', 5.2,
    1, '1h', '2026-03-08T18:36:22.482316'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3661,
    pnl_amount = 3.91,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C65CA837F75EC385', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-05-01 16:00:00', '2020-05-01 22:15:03', 1604.87248844, 1610.64326762,
    1580.79940111, 1644.99430065, 0.1177,
    0.3596, 4.23, 'TAKE_PROFIT', 6.25,
    1, '1h', '2026-03-08T18:36:22.476736'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3596,
    pnl_amount = 4.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BACE953E1A0AA978', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-05-02 02:00:00', '2020-05-02 05:00:02', 4525.07972855, 4513.39840745,
    4457.20353262, 4638.20672176, 0.0909,
    -0.2581, -2.35, 'TIME_EXIT', 3.0,
    0, '1h', '2026-03-08T18:36:22.476920'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2581,
    pnl_amount = -2.35,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9479268E6C97744C', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2020-05-05 17:00:00', '2020-05-05 19:42:47', 1852.67926116, 1858.09765446,
    1880.46945007, 1806.36227963, 0.0929,
    -0.2925, -2.72, 'STOP_LOSS', 2.71,
    0, '1h', '2026-03-08T18:36:22.483945'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2925,
    pnl_amount = -2.72,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '80052AD4E052A262', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-05-05 18:00:00', '2020-05-05 20:09:47', 4107.78010399, 4127.41929474,
    4046.16340243, 4210.47460659, 0.0899,
    0.4781, 4.3, 'TIME_EXIT', 2.16,
    1, '1h', '2026-03-08T18:36:22.481212'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4781,
    pnl_amount = 4.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '484BD71D498B656C', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-05-09 12:00:00', '2020-05-09 22:52:56', 265.65124936, 267.5029078,
    261.66648062, 272.2925306, 0.1155,
    0.697, 8.05, 'TAKE_PROFIT', 10.88,
    1, '1h', '2026-03-08T18:36:22.477021'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.697,
    pnl_amount = 8.05,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D06DB983AAFB03F1', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-05-09 12:00:00', '2020-05-09 20:30:48', 16335.44220815, 16379.24001708,
    16580.47384127, 15927.05615294, 0.0923,
    -0.2681, -2.47, 'TIME_EXIT', 8.51,
    0, '1h', '2026-03-08T18:36:22.483608'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2681,
    pnl_amount = -2.47,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '600BD227D5441E26', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-05-10 19:00:00', '2020-05-11 03:55:10', 1926.29114976, 1935.50349226,
    1897.39678252, 1974.44842851, 0.1139,
    0.4782, 5.45, 'TIME_EXIT', 8.92,
    1, '1h', '2026-03-08T18:36:22.479312'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4782,
    pnl_amount = 5.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9EABF7D3187CF6C6', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2020-05-10 20:00:00', '2020-05-11 06:17:26', 3966.17063596, 3945.03668665,
    4025.6631955, 3867.01637006, 0.0813,
    0.5329, 4.33, 'TRAILING_STOP', 10.29,
    1, '1h', '2026-03-08T18:36:22.477276'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5329,
    pnl_amount = 4.33,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1EB81778D522E529', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-05-11 03:00:00', '2020-05-11 10:07:33', 1962.76499464, 1973.42709525,
    1933.32351972, 2011.8341195, 0.0843,
    0.5432, 4.58, 'TIME_EXIT', 7.13,
    1, '1h', '2026-03-08T18:36:22.481023'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5432,
    pnl_amount = 4.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '979C85C1B98B56E2', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-05-13 04:00:00', '2020-05-13 09:06:05', 878.28461862, 881.81903678,
    865.11034934, 900.24173409, 0.1042,
    0.4024, 4.19, 'TRAILING_STOP', 5.1,
    1, '1h', '2026-03-08T18:36:22.482958'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4024,
    pnl_amount = 4.19,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9436A0DA944B63B8', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-05-17 07:00:00', '2020-05-17 15:21:40', 5435.46675119, 5452.88759347,
    5516.99875246, 5299.58008241, 0.0957,
    -0.3205, -3.07, 'STOP_LOSS', 8.36,
    0, '1h', '2026-03-08T18:36:22.483814'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3205,
    pnl_amount = -3.07,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3C17DC0068CFFA6B', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-05-20 10:00:00', '2020-05-20 13:35:27', 2511.96098198, 2502.12936213,
    2549.64039671, 2449.16195743, 0.1053,
    0.3914, 4.12, 'TIME_EXIT', 3.59,
    1, '1h', '2026-03-08T18:36:22.483456'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3914,
    pnl_amount = 4.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '95B18F058387AD72', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-05-22 06:00:00', '2020-05-22 11:53:12', 2791.02295761, 2808.22242167,
    2749.15761325, 2860.79853155, 0.105,
    0.6162, 6.47, 'TIME_EXIT', 5.89,
    1, '1h', '2026-03-08T18:36:22.476011'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6162,
    pnl_amount = 6.47,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6D0C19511DC6207F', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-05-22 19:00:00', '2020-05-23 04:53:10', 3469.44227534, 3456.84883838,
    3521.48390947, 3382.70621846, 0.0844,
    0.363, 3.06, 'TAKE_PROFIT', 9.89,
    1, '1h', '2026-03-08T18:36:22.477595'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.363,
    pnl_amount = 3.06,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '444C9DD0CC8DAA71', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-05-28 13:00:00', '2020-05-29 00:16:17', 1594.55359967, 1604.91538541,
    1570.63529568, 1634.41743967, 0.0827,
    0.6498, 5.38, 'TRAILING_STOP', 11.27,
    1, '1h', '2026-03-08T18:36:22.476080'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6498,
    pnl_amount = 5.38,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4CA1B8D76864371B', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2020-05-29 00:00:00', '2020-05-29 02:54:28', 3735.89795532, 3751.4947393,
    3679.85948599, 3829.29540421, 0.0913,
    0.4175, 3.81, 'TAKE_PROFIT', 2.91,
    1, '1h', '2026-03-08T18:36:22.476304'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4175,
    pnl_amount = 3.81,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F800370B949D78F8', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-05-30 14:00:00', '2020-05-31 00:24:30', 3299.20192826, 3309.10066732,
    3348.68995718, 3216.72188005, 0.0905,
    -0.3, -2.72, 'TIME_EXIT', 10.41,
    0, '1h', '2026-03-08T18:36:22.484083'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3,
    pnl_amount = -2.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E164A3B60A9A333F', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-06-01 16:00:00', '2020-06-01 22:54:49', 3453.46591201, 3464.41389606,
    3505.26790069, 3367.12926421, 0.084,
    -0.317, -2.66, 'TIME_EXIT', 6.91,
    0, '1h', '2026-03-08T18:36:22.480489'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.317,
    pnl_amount = -2.66,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C5DAC8F283E2AE6C', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2020-06-03 03:00:00', '2020-06-03 08:44:51', 1198.65605696, 1206.62171159,
    1180.67621611, 1228.62245839, 0.1134,
    0.6645, 7.53, 'TRAILING_STOP', 5.75,
    1, '1h', '2026-03-08T18:36:22.480659'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6645,
    pnl_amount = 7.53,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '203DEE3220554331', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-06-09 14:00:00', '2020-06-09 17:42:48', 1303.0023374, 1309.54546335,
    1283.45730234, 1335.57739584, 0.1181,
    0.5022, 5.93, 'TAKE_PROFIT', 3.71,
    1, '1h', '2026-03-08T18:36:22.480779'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5022,
    pnl_amount = 5.93,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA15F9C25C775476', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-06-10 03:00:00', '2020-06-10 07:03:07', 1864.83296614, 1876.4464736,
    1836.86047165, 1911.4537903, 0.0992,
    0.6228, 6.18, 'TAKE_PROFIT', 4.05,
    1, '1h', '2026-03-08T18:36:22.478771'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6228,
    pnl_amount = 6.18,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C1C3AD8D65396B47', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-06-11 09:00:00', '2020-06-11 18:34:10', 507.02904416, 510.50296634,
    499.4236085, 519.70477027, 0.0849,
    0.6852, 5.82, 'TAKE_PROFIT', 9.57,
    1, '1h', '2026-03-08T18:36:22.480891'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6852,
    pnl_amount = 5.82,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C060E11B10E71292', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-06-11 17:00:00', '2020-06-11 19:07:44', 2295.17717845, 2306.78761419,
    2260.74952078, 2352.55660792, 0.1191,
    0.5059, 6.03, 'TRAILING_STOP', 2.13,
    1, '1h', '2026-03-08T18:36:22.481294'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5059,
    pnl_amount = 6.03,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A53D9B440FD09DB4', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-06-12 15:00:00', '2020-06-12 23:20:36', 586.22050031, 583.76481841,
    595.01380781, 571.5649878, 0.1061,
    0.4189, 4.45, 'TAKE_PROFIT', 8.34,
    1, '1h', '2026-03-08T18:36:22.475815'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4189,
    pnl_amount = 4.45,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '08A402A0DA7A729B', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-06-13 01:00:00', '2020-06-13 04:12:11', 4892.84429405, 4915.10991338,
    4819.45162964, 5015.1654014, 0.1085,
    0.4551, 4.94, 'TRAILING_STOP', 3.2,
    1, '1h', '2026-03-08T18:36:22.480818'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4551,
    pnl_amount = 4.94,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75E8817380CF8F65', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-06-14 02:00:00', '2020-06-14 12:24:01', 376.93240188, 378.35364607,
    382.5863879, 367.50909183, 0.1178,
    -0.3771, -4.44, 'STOP_LOSS', 10.4,
    0, '1h', '2026-03-08T18:36:22.483671'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3771,
    pnl_amount = -4.44,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2FB7B80BCA3AB2A8', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-06-16 11:00:00', '2020-06-16 15:26:33', 1667.21252175, 1658.00247858,
    1692.22070958, 1625.53220871, 0.0918,
    0.5524, 5.07, 'TRAILING_STOP', 4.44,
    1, '1h', '2026-03-08T18:36:22.479755'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5524,
    pnl_amount = 5.07,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EFC0F8F35E1E6F64', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2020-06-17 06:00:00', '2020-06-17 14:14:58', 1674.85019537, 1679.70921738,
    1699.9729483, 1632.97894049, 0.1164,
    -0.2901, -3.38, 'TIME_EXIT', 8.25,
    0, '1h', '2026-03-08T18:36:22.480921'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2901,
    pnl_amount = -3.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C6C1861342C12F4D', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2020-06-17 20:00:00', '2020-06-17 23:49:10', 104.18103633, 104.68488299,
    102.61832079, 106.78556224, 0.1067,
    0.4836, 5.16, 'TRAILING_STOP', 3.82,
    1, '1h', '2026-03-08T18:36:22.477204'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4836,
    pnl_amount = 5.16,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '365D2BAC4D5E59C5', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-06-19 04:00:00', '2020-06-19 12:09:36', 751.07773973, 746.19346043,
    762.34390582, 732.30079624, 0.1022,
    0.6503, 6.64, 'TAKE_PROFIT', 8.16,
    1, '1h', '2026-03-08T18:36:22.483117'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6503,
    pnl_amount = 6.64,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5C55DFADB91BA165', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-06-20 09:00:00', '2020-06-20 13:33:11', 2731.57162469, 2747.19328294,
    2690.59805032, 2799.8609153, 0.1009,
    0.5719, 5.77, 'TAKE_PROFIT', 4.55,
    1, '1h', '2026-03-08T18:36:22.478642'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5719,
    pnl_amount = 5.77,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '274E6F0E91D5E7D8', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2020-06-26 04:00:00', '2020-06-26 08:47:07', 4234.4121377, 4215.84844628,
    4297.92831977, 4128.55183426, 0.1025,
    0.4384, 4.49, 'TIME_EXIT', 4.79,
    1, '1h', '2026-03-08T18:36:22.481832'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4384,
    pnl_amount = 4.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5B44C61F73FC7B4F', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2020-06-26 21:00:00', '2020-06-27 08:06:20', 921.62108258, 917.7282975,
    935.44539882, 898.58055552, 0.0903,
    0.4224, 3.81, 'TAKE_PROFIT', 11.11,
    1, '1h', '2026-03-08T18:36:22.481805'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4224,
    pnl_amount = 3.81,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7DD0A40F7BC862D3', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-06-28 00:00:00', '2020-06-28 09:48:17', 11745.13648609, 11700.46903477,
    11921.31353339, 11451.50807394, 0.1082,
    0.3803, 4.11, 'TAKE_PROFIT', 9.8,
    1, '1h', '2026-03-08T18:36:22.479444'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3803,
    pnl_amount = 4.11,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8C93817F4FDED9F1', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-06-28 02:00:00', '2020-06-28 12:50:11', 3622.50314261, 3640.67873143,
    3568.16559548, 3713.06572118, 0.0927,
    0.5017, 4.65, 'TRAILING_STOP', 10.84,
    1, '1h', '2026-03-08T18:36:22.479888'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5017,
    pnl_amount = 4.65,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '08DF2D58442442F6', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-07-06 07:00:00', '2020-07-06 15:43:49', 131.74243588, 132.57171281,
    129.76629934, 135.03599677, 0.0951,
    0.6295, 5.99, 'TAKE_PROFIT', 8.73,
    1, '1h', '2026-03-08T18:36:22.479194'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6295,
    pnl_amount = 5.99,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '595DACE1D87AC9A5', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-07-08 05:00:00', '2020-07-08 12:01:31', 18177.06106056, 18232.40328742,
    18449.71697647, 17722.63453405, 0.1015,
    -0.3045, -3.09, 'STOP_LOSS', 7.03,
    0, '1h', '2026-03-08T18:36:22.478156'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3045,
    pnl_amount = -3.09,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '03BFBF7FC2A79235', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-07-16 19:00:00', '2020-07-17 00:34:21', 2288.31674339, 2281.9717625,
    2253.99199224, 2345.52466198, 0.1043,
    -0.2773, -2.89, 'TIME_EXIT', 5.57,
    0, '1h', '2026-03-08T18:36:22.482507'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2773,
    pnl_amount = -2.89,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EADD1F60A1E920E8', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-07-17 23:00:00', '2020-07-18 02:50:37', 17540.82869947, 17446.86372723,
    17803.94112996, 17102.30798198, 0.1022,
    0.5357, 5.47, 'TRAILING_STOP', 3.84,
    1, '1h', '2026-03-08T18:36:22.483700'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5357,
    pnl_amount = 5.47,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3E9EF9C615A83B67', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-07-18 10:00:00', '2020-07-18 19:59:04', 989.50854267, 986.0093119,
    1004.35117081, 964.7708291, 0.0873,
    0.3536, 3.09, 'TIME_EXIT', 9.98,
    1, '1h', '2026-03-08T18:36:22.483796'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3536,
    pnl_amount = 3.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F746CA23EC60E03D', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2020-07-20 12:00:00', '2020-07-20 23:59:15', 624.90290371, 623.26025543,
    615.52936015, 640.5254763, 0.0862,
    -0.2629, -2.26, 'TIME_EXIT', 11.99,
    0, '1h', '2026-03-08T18:36:22.475855'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2629,
    pnl_amount = -2.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5C2EA947BC369BAC', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-07-21 00:00:00', '2020-07-21 06:39:54', 4712.58083681, 4742.54483654,
    4641.89212426, 4830.39535773, 0.1121,
    0.6358, 7.13, 'TAKE_PROFIT', 6.67,
    1, '1h', '2026-03-08T18:36:22.478866'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6358,
    pnl_amount = 7.13,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9F4D06820BFA137F', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-07-24 08:00:00', '2020-07-24 10:37:58', 49831.16476332, 50142.43127431,
    49083.69729187, 51076.9438824, 0.0901,
    0.6246, 5.63, 'TRAILING_STOP', 2.63,
    1, '1h', '2026-03-08T18:36:22.477932'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6246,
    pnl_amount = 5.63,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1456D92E83AA2738', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-07-24 19:00:00', '2020-07-25 03:49:16', 2672.42336864, 2655.9136732,
    2712.50971917, 2605.61278442, 0.1188,
    0.6178, 7.34, 'TIME_EXIT', 8.82,
    1, '1h', '2026-03-08T18:36:22.476461'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6178,
    pnl_amount = 7.34,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D711FE02C3D6D9C4', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-07-25 21:00:00', '2020-07-26 05:10:05', 932.47088773, 926.0786899,
    946.45795104, 909.15911553, 0.1151,
    0.6855, 7.89, 'TIME_EXIT', 8.17,
    1, '1h', '2026-03-08T18:36:22.482325'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6855,
    pnl_amount = 7.89,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AE298D66927D9C99', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-08-01 16:00:00', '2020-08-01 21:18:22', 798.2956374, 802.82160478,
    786.32120284, 818.25302834, 0.0862,
    0.567, 4.89, 'TIME_EXIT', 5.31,
    1, '1h', '2026-03-08T18:36:22.477168'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.567,
    pnl_amount = 4.89,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '58E9010DF0225DB4', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-08-03 16:00:00', '2020-08-04 01:11:31', 1927.82363025, 1921.15760472,
    1898.90627579, 1976.019221, 0.0959,
    -0.3458, -3.31, 'TIME_EXIT', 9.19,
    0, '1h', '2026-03-08T18:36:22.476246'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3458,
    pnl_amount = -3.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '082389F925C63723', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-08-04 16:00:00', '2020-08-04 19:42:35', 40470.48875453, 40301.02184659,
    41077.54608585, 39458.72653567, 0.116,
    0.4187, 4.86, 'TRAILING_STOP', 3.71,
    1, '1h', '2026-03-08T18:36:22.482854'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4187,
    pnl_amount = 4.86,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '467B8E1EDA5CED95', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-08-05 01:00:00', '2020-08-05 06:14:58', 2551.82076827, 2566.75829123,
    2513.54345675, 2615.61628748, 0.0916,
    0.5854, 5.36, 'TAKE_PROFIT', 5.25,
    1, '1h', '2026-03-08T18:36:22.475864'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5854,
    pnl_amount = 5.36,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '001B9EEC3FBFEA33', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-08-06 06:00:00', '2020-08-06 08:38:57', 223.75495417, 223.09283226,
    220.39862985, 229.34882802, 0.1197,
    -0.2959, -3.54, 'STOP_LOSS', 2.65,
    0, '1h', '2026-03-08T18:36:22.477159'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2959,
    pnl_amount = -3.54,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2A9F483A862AC5D1', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-08-07 08:00:00', '2020-08-07 10:20:01', 3934.27873897, 3914.58212912,
    3993.29292006, 3835.9217705, 0.1092,
    0.5006, 5.46, 'TIME_EXIT', 2.33,
    1, '1h', '2026-03-08T18:36:22.475792'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5006,
    pnl_amount = 5.46,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1042D737FB807729', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-08-09 01:00:00', '2020-08-09 09:09:24', 4387.70218231, 4359.28065479,
    4453.51771504, 4278.00962775, 0.1046,
    0.6478, 6.78, 'TAKE_PROFIT', 8.16,
    1, '1h', '2026-03-08T18:36:22.479248'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6478,
    pnl_amount = 6.78,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C66630216EC4D249', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2020-08-11 03:00:00', '2020-08-11 13:53:56', 2905.17199211, 2885.3500902,
    2948.74957199, 2832.5426923, 0.0858,
    0.6823, 5.85, 'TIME_EXIT', 10.9,
    1, '1h', '2026-03-08T18:36:22.478041'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6823,
    pnl_amount = 5.85,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C4C048EF4F3178B2', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2020-08-16 07:00:00', '2020-08-16 11:51:13', 407.06726773, 404.84730176,
    413.17327674, 396.89058603, 0.0843,
    0.5454, 4.59, 'TAKE_PROFIT', 4.85,
    1, '1h', '2026-03-08T18:36:22.476782'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5454,
    pnl_amount = 4.59,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FBA5F1A09AC01B63', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2020-08-18 13:00:00', '2020-08-18 19:19:01', 3886.79934411, 3899.04461874,
    3945.10133427, 3789.62936051, 0.111,
    -0.315, -3.5, 'TIME_EXIT', 6.32,
    0, '1h', '2026-03-08T18:36:22.480414'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.315,
    pnl_amount = -3.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0A2E85A8E9122F1B', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-08-19 22:00:00', '2020-08-20 07:03:38', 12416.37658499, 12356.34392061,
    12602.62223377, 12105.96717037, 0.0833,
    0.4835, 4.03, 'TAKE_PROFIT', 9.06,
    1, '1h', '2026-03-08T18:36:22.482765'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4835,
    pnl_amount = 4.03,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '15ED3EE6F8507526', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-08-21 12:00:00', '2020-08-21 15:59:54', 2827.03565592, 2839.29173718,
    2784.63012108, 2897.71154732, 0.0972,
    0.4335, 4.21, 'TIME_EXIT', 4.0,
    1, '1h', '2026-03-08T18:36:22.478383'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4335,
    pnl_amount = 4.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8B4C1301395D9A75', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-08-21 19:00:00', '2020-08-21 21:22:22', 235.42155866, 234.1259513,
    238.95288204, 229.53601969, 0.0804,
    0.5503, 4.42, 'TRAILING_STOP', 2.37,
    1, '1h', '2026-03-08T18:36:22.479612'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5503,
    pnl_amount = 4.42,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6D389CDF95150A99', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2020-08-25 20:00:00', '2020-08-26 01:16:45', 737.11922386, 731.98460757,
    748.17601222, 718.69124326, 0.0885,
    0.6966, 6.16, 'TRAILING_STOP', 5.28,
    1, '1h', '2026-03-08T18:36:22.477347'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6966,
    pnl_amount = 6.16,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D767FC989236EBC0', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-08-27 17:00:00', '2020-08-28 00:47:35', 35860.41261294, 36045.10723385,
    35322.50642375, 36756.92292827, 0.0856,
    0.515, 4.41, 'TAKE_PROFIT', 7.79,
    1, '1h', '2026-03-08T18:36:22.480912'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.515,
    pnl_amount = 4.41,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D68841986A3D5236', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-08-27 20:00:00', '2020-08-28 00:48:01', 1569.82358161, 1560.43453443,
    1593.37093534, 1530.57799207, 0.0936,
    0.5981, 5.6, 'TAKE_PROFIT', 4.8,
    1, '1h', '2026-03-08T18:36:22.480261'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5981,
    pnl_amount = 5.6,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F72A0F3E4B326CB', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-08-28 21:00:00', '2020-08-28 23:55:17', 1999.52432606, 2009.34374729,
    1969.53146117, 2049.51243421, 0.0957,
    0.4911, 4.7, 'TIME_EXIT', 2.92,
    1, '1h', '2026-03-08T18:36:22.479665'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4911,
    pnl_amount = 4.7,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5CA8127BD90D30F7', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-08-29 20:00:00', '2020-08-30 02:31:18', 15277.06631892, 15363.27475561,
    15047.91032414, 15658.99297689, 0.1186,
    0.5643, 6.69, 'TRAILING_STOP', 6.52,
    1, '1h', '2026-03-08T18:36:22.478270'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5643,
    pnl_amount = 6.69,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6C926D1D28FCD385', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2020-08-31 06:00:00', '2020-08-31 12:07:58', 4407.72238106, 4390.96259327,
    4473.83821677, 4297.52932153, 0.0869,
    0.3802, 3.31, 'TIME_EXIT', 6.13,
    1, '1h', '2026-03-08T18:36:22.478467'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3802,
    pnl_amount = 3.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '629399F1DE483425', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2020-09-01 03:00:00', '2020-09-01 14:50:44', 2687.16477423, 2674.02148566,
    2727.47224585, 2619.98565488, 0.0997,
    0.4891, 4.88, 'TAKE_PROFIT', 11.85,
    1, '1h', '2026-03-08T18:36:22.483202'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4891,
    pnl_amount = 4.88,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DD9D237B0C2BB8DE', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-09-03 02:00:00', '2020-09-03 05:59:57', 1875.55847461, 1885.91406809,
    1847.42509749, 1922.44743647, 0.1057,
    0.5521, 5.83, 'TIME_EXIT', 4.0,
    1, '1h', '2026-03-08T18:36:22.482666'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5521,
    pnl_amount = 5.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EF5DEFCD0012A2F8', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-09-04 12:00:00', '2020-09-04 17:21:20', 3414.04487439, 3427.46788993,
    3362.83420127, 3499.39599625, 0.0835,
    0.3932, 3.28, 'TAKE_PROFIT', 5.36,
    1, '1h', '2026-03-08T18:36:22.476855'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3932,
    pnl_amount = 3.28,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F08347C62B4AA389', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-09-06 12:00:00', '2020-09-06 15:04:17', 393.27518246, 394.35455675,
    399.1743102, 383.4433029, 0.1146,
    -0.2745, -3.15, 'TIME_EXIT', 3.07,
    0, '1h', '2026-03-08T18:36:22.476801'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2745,
    pnl_amount = -3.15,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '465C860120B221B5', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-09-07 06:00:00', '2020-09-07 12:04:44', 19692.58640641, 19788.51685372,
    19397.19761031, 20184.90106657, 0.114,
    0.4871, 5.55, 'TIME_EXIT', 6.08,
    1, '1h', '2026-03-08T18:36:22.476639'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4871,
    pnl_amount = 5.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '15016EB8639BAA44', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-09-07 14:00:00', '2020-09-07 17:45:18', 3908.96028263, 3928.43567072,
    3850.32587839, 4006.68428969, 0.1139,
    0.4982, 5.68, 'TIME_EXIT', 3.76,
    1, '1h', '2026-03-08T18:36:22.483355'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4982,
    pnl_amount = 5.68,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '830D2FD245E5967A', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-09-10 02:00:00', '2020-09-10 08:36:30', 4760.90701101, 4747.60338031,
    4689.49340585, 4879.92968629, 0.0936,
    -0.2794, -2.62, 'TIME_EXIT', 6.61,
    0, '1h', '2026-03-08T18:36:22.482426'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2794,
    pnl_amount = -2.62,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A893541B2591D9D', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-09-12 23:00:00', '2020-09-13 08:52:23', 2615.69460492, 2602.82222834,
    2654.93002399, 2550.30223979, 0.0952,
    0.4921, 4.69, 'TIME_EXIT', 9.87,
    1, '1h', '2026-03-08T18:36:22.480207'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4921,
    pnl_amount = 4.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A0452BDD74DB57B8', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-09-14 03:00:00', '2020-09-14 12:01:35', 3020.10911156, 3003.73657717,
    3065.41074823, 2944.60638377, 0.0975,
    0.5421, 5.29, 'TAKE_PROFIT', 9.03,
    1, '1h', '2026-03-08T18:36:22.478888'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5421,
    pnl_amount = 5.29,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A217B69E17B3D345', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-09-14 14:00:00', '2020-09-14 19:16:15', 31974.89843835, 31873.24615652,
    31495.27496178, 32774.27089931, 0.0831,
    -0.3179, -2.64, 'TIME_EXIT', 5.27,
    0, '1h', '2026-03-08T18:36:22.476549'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3179,
    pnl_amount = -2.64,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '343184864BDAF2AD', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-09-17 22:00:00', '2020-09-18 09:41:06', 20351.89964444, 20416.28789601,
    20657.1781391, 19843.10215333, 0.0922,
    -0.3164, -2.92, 'TIME_EXIT', 11.69,
    0, '1h', '2026-03-08T18:36:22.484124'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3164,
    pnl_amount = -2.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '26AA51914AFCF449', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2020-09-19 00:00:00', '2020-09-19 07:46:41', 4748.33336273, 4725.90373079,
    4819.55836317, 4629.62502866, 0.0924,
    0.4724, 4.37, 'TIME_EXIT', 7.78,
    1, '1h', '2026-03-08T18:36:22.479701'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4724,
    pnl_amount = 4.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DE5562FF7CCCA8C4', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-09-19 07:00:00', '2020-09-19 14:28:54', 632.64262475, 635.20197311,
    623.15298538, 648.45869037, 0.0957,
    0.4045, 3.87, 'TAKE_PROFIT', 7.48,
    1, '1h', '2026-03-08T18:36:22.478597'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4045,
    pnl_amount = 3.87,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '74F10E4888A5DA6B', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-09-20 14:00:00', '2020-09-20 21:03:19', 3399.25885333, 3390.36263673,
    3348.26997053, 3484.24032467, 0.0911,
    -0.2617, -2.39, 'STOP_LOSS', 7.06,
    0, '1h', '2026-03-08T18:36:22.477830'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2617,
    pnl_amount = -2.39,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CDCF3B6E5D470B84', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-09-22 02:00:00', '2020-09-22 08:14:02', 10500.9923201, 10438.73705053,
    10658.5072049, 10238.4675121, 0.0968,
    0.5929, 5.74, 'TRAILING_STOP', 6.23,
    1, '1h', '2026-03-08T18:36:22.480423'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5929,
    pnl_amount = 5.74,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F861EE7A650B8CC2', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-09-24 19:00:00', '2020-09-24 21:22:15', 3134.9415297, 3155.32877701,
    3087.91740676, 3213.31506794, 0.114,
    0.6503, 7.42, 'TIME_EXIT', 2.37,
    1, '1h', '2026-03-08T18:36:22.478298'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6503,
    pnl_amount = 7.42,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E01A55EB5437C1A3', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2020-10-02 12:00:00', '2020-10-02 17:08:41', 2340.51373869, 2348.79704265,
    2375.62144477, 2282.00089522, 0.1152,
    -0.3539, -4.08, 'STOP_LOSS', 5.14,
    0, '1h', '2026-03-08T18:36:22.477257'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3539,
    pnl_amount = -4.08,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C9B12344240C5529', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-10-06 07:00:00', '2020-10-06 16:02:36', 680.45861052, 676.40541315,
    690.66548968, 663.44714526, 0.1104,
    0.5957, 6.58, 'TRAILING_STOP', 9.04,
    1, '1h', '2026-03-08T18:36:22.477452'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5957,
    pnl_amount = 6.58,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2E8D753639AFD53C', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-10-10 04:00:00', '2020-10-10 15:41:47', 29511.66926448, 29370.86074158,
    29954.34430345, 28773.87753287, 0.0854,
    0.4771, 4.07, 'TRAILING_STOP', 11.7,
    1, '1h', '2026-03-08T18:36:22.476674'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4771,
    pnl_amount = 4.07,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '93E714B0917EF525', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-10-14 16:00:00', '2020-10-15 01:15:22', 1677.91837367, 1684.13839244,
    1652.74959807, 1719.86633301, 0.0965,
    0.3707, 3.58, 'TRAILING_STOP', 9.26,
    1, '1h', '2026-03-08T18:36:22.481359'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3707,
    pnl_amount = 3.58,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EBA89EE1AA330CDB', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2020-10-14 18:00:00', '2020-10-15 03:50:53', 4949.33726522, 4935.7637395,
    4875.09720625, 5073.07069686, 0.1006,
    -0.2742, -2.76, 'TIME_EXIT', 9.85,
    0, '1h', '2026-03-08T18:36:22.483777'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2742,
    pnl_amount = -2.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D8D77636AC3B918E', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-10-15 12:00:00', '2020-10-15 23:36:18', 373.22105913, 375.33427749,
    367.62274325, 382.55158561, 0.117,
    0.5662, 6.62, 'TIME_EXIT', 11.61,
    1, '1h', '2026-03-08T18:36:22.480073'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5662,
    pnl_amount = 6.62,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '39BE939C447963C4', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-10-19 00:00:00', '2020-10-19 11:54:48', 42242.13699245, 42016.8498282,
    42875.76904733, 41186.08356764, 0.0878,
    0.5333, 4.68, 'TIME_EXIT', 11.91,
    1, '1h', '2026-03-08T18:36:22.483337'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5333,
    pnl_amount = 4.68,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7ED1F2AE29894F17', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-10-22 15:00:00', '2020-10-23 02:26:26', 3373.04693758, 3360.53854253,
    3322.45123352, 3457.37311102, 0.1114,
    -0.3708, -4.13, 'STOP_LOSS', 11.44,
    0, '1h', '2026-03-08T18:36:22.483087'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3708,
    pnl_amount = -4.13,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6BA1FAE3A4C81179', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-10-23 15:00:00', '2020-10-24 00:02:09', 38874.94889559, 38630.96522544,
    39458.07312903, 37903.0751732, 0.0887,
    0.6276, 5.57, 'TIME_EXIT', 9.04,
    1, '1h', '2026-03-08T18:36:22.479453'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6276,
    pnl_amount = 5.57,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '12C8E30BD7F522E8', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-10-24 06:00:00', '2020-10-24 12:35:14', 1463.34163356, 1458.17599004,
    1441.39150906, 1499.9251744, 0.0858,
    -0.353, -3.03, 'TIME_EXIT', 6.59,
    0, '1h', '2026-03-08T18:36:22.479000'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.353,
    pnl_amount = -3.03,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2639A21D48409610', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-10-24 15:00:00', '2020-10-24 17:11:53', 1959.55735055, 1951.49551878,
    1988.95071081, 1910.56841678, 0.0879,
    0.4114, 3.62, 'TAKE_PROFIT', 2.2,
    1, '1h', '2026-03-08T18:36:22.478615'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4114,
    pnl_amount = 3.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EB866B46E28B62C7', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-10-26 05:00:00', '2020-10-26 13:45:00', 405.65069586, 404.46554098,
    399.56593542, 415.79196326, 0.1093,
    -0.2922, -3.19, 'STOP_LOSS', 8.75,
    0, '1h', '2026-03-08T18:36:22.484133'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2922,
    pnl_amount = -3.19,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AEAA311BF387450D', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2020-10-26 13:00:00', '2020-10-26 17:45:24', 2588.65868384, 2572.5038838,
    2627.48856409, 2523.94221674, 0.0925,
    0.6241, 5.77, 'TAKE_PROFIT', 4.76,
    1, '1h', '2026-03-08T18:36:22.477505'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6241,
    pnl_amount = 5.77,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A1E20C3637BFBDEA', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-10-27 09:00:00', '2020-10-27 16:06:40', 4718.65003024, 4704.98085646,
    4647.87027979, 4836.616281, 0.1135,
    -0.2897, -3.29, 'STOP_LOSS', 7.11,
    0, '1h', '2026-03-08T18:36:22.475805'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2897,
    pnl_amount = -3.29,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DC6B1BAEB60993FB', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-10-28 16:00:00', '2020-10-28 20:15:12', 42434.33398861, 42152.13490217,
    43070.84899843, 41373.47563889, 0.1059,
    0.665, 7.04, 'TIME_EXIT', 4.25,
    1, '1h', '2026-03-08T18:36:22.480686'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.665,
    pnl_amount = 7.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0117638EA5FE9245', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2020-10-29 07:00:00', '2020-10-29 10:12:33', 2107.20095562, 2093.313554,
    2138.80896995, 2054.52093173, 0.0985,
    0.659, 6.49, 'TRAILING_STOP', 3.21,
    1, '1h', '2026-03-08T18:36:22.476294'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.659,
    pnl_amount = 6.49,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AB24ABA54E0B77FF', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-10-29 09:00:00', '2020-10-29 16:48:16', 4864.87034696, 4877.72902481,
    4937.84340216, 4743.24858828, 0.0835,
    -0.2643, -2.21, 'STOP_LOSS', 7.8,
    0, '1h', '2026-03-08T18:36:22.482801'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2643,
    pnl_amount = -2.21,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '39630ACD9C607D9A', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-10-31 04:00:00', '2020-10-31 07:20:42', 1613.15427021, 1623.89567482,
    1588.95695615, 1653.48312696, 0.1035,
    0.6659, 6.89, 'TAKE_PROFIT', 3.35,
    1, '1h', '2026-03-08T18:36:22.477605'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6659,
    pnl_amount = 6.89,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C56B8E852D482B21', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2020-11-06 03:00:00', '2020-11-06 10:27:38', 2543.00422455, 2551.03763229,
    2581.14928791, 2479.42911893, 0.0859,
    -0.3159, -2.71, 'TIME_EXIT', 7.46,
    0, '1h', '2026-03-08T18:36:22.483320'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3159,
    pnl_amount = -2.71,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A0DCA234336004F4', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-11-06 15:00:00', '2020-11-06 19:16:40', 77.09465272, 77.32285199,
    78.25107251, 75.1672864, 0.086,
    -0.296, -2.55, 'STOP_LOSS', 4.28,
    0, '1h', '2026-03-08T18:36:22.481041'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.296,
    pnl_amount = -2.55,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '32208A3306DEA6BB', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-11-09 08:00:00', '2020-11-09 13:49:37', 4697.98503098, 4712.39500477,
    4768.45480644, 4580.53540521, 0.0801,
    -0.3067, -2.46, 'STOP_LOSS', 5.83,
    0, '1h', '2026-03-08T18:36:22.479186'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3067,
    pnl_amount = -2.46,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '517293C5818F6495', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-11-12 11:00:00', '2020-11-12 13:52:42', 1190.75550301, 1194.52144038,
    1208.61683555, 1160.98661543, 0.1052,
    -0.3163, -3.33, 'TIME_EXIT', 2.88,
    0, '1h', '2026-03-08T18:36:22.482601'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3163,
    pnl_amount = -3.33,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CEDAF1C555FA1349', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-11-16 03:00:00', '2020-11-16 10:29:43', 6925.46771737, 6901.22741594,
    7029.34973314, 6752.33102444, 0.1143,
    0.35, 4.0, 'TIME_EXIT', 7.5,
    1, '1h', '2026-03-08T18:36:22.483311'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.35,
    pnl_amount = 4.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC64F1AFE265B91C', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2020-11-20 21:00:00', '2020-11-20 23:32:41', 2191.05763551, 2198.60012447,
    2223.92350005, 2136.28119463, 0.1064,
    -0.3442, -3.66, 'STOP_LOSS', 2.54,
    0, '1h', '2026-03-08T18:36:22.481684'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3442,
    pnl_amount = -3.66,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0C2AD89E581778C9', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-11-21 06:00:00', '2020-11-21 13:37:02', 3006.59159051, 2996.87973115,
    2961.49271665, 3081.75638027, 0.1087,
    -0.323, -3.51, 'TIME_EXIT', 7.62,
    0, '1h', '2026-03-08T18:36:22.483927'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.323,
    pnl_amount = -3.51,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7E729D85A77ED396', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2020-11-21 23:00:00', '2020-11-22 07:02:55', 4753.52187103, 4737.36607483,
    4682.21904296, 4872.3599178, 0.1039,
    -0.3399, -3.53, 'STOP_LOSS', 8.05,
    0, '1h', '2026-03-08T18:36:22.482096'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3399,
    pnl_amount = -3.53,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B26DBCE34E60F37C', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-11-24 18:00:00', '2020-11-25 01:42:20', 2946.15081582, 2932.90093827,
    2990.34307806, 2872.49704543, 0.1018,
    0.4497, 4.58, 'TRAILING_STOP', 7.71,
    1, '1h', '2026-03-08T18:36:22.482874'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4497,
    pnl_amount = 4.58,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CEAB8DDB79E4FB82', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-12-02 08:00:00', '2020-12-02 13:18:13', 4398.49340353, 4383.98571707,
    4332.51600248, 4508.45573862, 0.1144,
    -0.3298, -3.77, 'TIME_EXIT', 5.3,
    0, '1h', '2026-03-08T18:36:22.477970'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3298,
    pnl_amount = -3.77,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BD41880D5C0BF00F', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-12-03 11:00:00', '2020-12-03 17:19:43', 1500.59537228, 1494.32209319,
    1523.10430286, 1463.08048797, 0.099,
    0.4181, 4.14, 'TIME_EXIT', 6.33,
    1, '1h', '2026-03-08T18:36:22.477642'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4181,
    pnl_amount = 4.14,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FE520DEDD8692B72', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2020-12-03 15:00:00', '2020-12-03 21:29:25', 45048.93606161, 44752.8578726,
    45724.67010254, 43922.71266007, 0.1141,
    0.6572, 7.5, 'TRAILING_STOP', 6.49,
    1, '1h', '2026-03-08T18:36:22.483535'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6572,
    pnl_amount = 7.5,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ED772C271AB75D73', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2020-12-06 16:00:00', '2020-12-06 18:28:02', 2807.00169148, 2797.32642866,
    2764.89666611, 2877.17673377, 0.1198,
    -0.3447, -4.13, 'TIME_EXIT', 2.47,
    0, '1h', '2026-03-08T18:36:22.480845'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3447,
    pnl_amount = -4.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E86C06125922A176', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-12-07 08:00:00', '2020-12-07 13:07:21', 4135.69681845, 4151.13723045,
    4197.73227073, 4032.30439799, 0.1017,
    -0.3733, -3.8, 'STOP_LOSS', 5.12,
    0, '1h', '2026-03-08T18:36:22.476126'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3733,
    pnl_amount = -3.8,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '48E9346F20DECA2D', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2020-12-09 06:00:00', '2020-12-09 13:32:37', 4196.7882921, 4214.20281503,
    4133.83646772, 4301.7079994, 0.1196,
    0.4149, 4.96, 'TRAILING_STOP', 7.54,
    1, '1h', '2026-03-08T18:36:22.479107'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4149,
    pnl_amount = 4.96,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A142239B93B7B6E0', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-12-10 02:00:00', '2020-12-10 08:33:29', 4466.0145472, 4443.63723943,
    4533.00476541, 4354.36418352, 0.1083,
    0.5011, 5.43, 'TAKE_PROFIT', 6.56,
    1, '1h', '2026-03-08T18:36:22.479971'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5011,
    pnl_amount = 5.43,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '15F758E752CFC67F', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2020-12-16 07:00:00', '2020-12-16 16:09:46', 1706.23887942, 1696.58359139,
    1731.83246262, 1663.58290744, 0.0803,
    0.5659, 4.55, 'TIME_EXIT', 9.16,
    1, '1h', '2026-03-08T18:36:22.477877'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5659,
    pnl_amount = 4.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6D79BB79E9566A30', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2020-12-22 13:00:00', '2020-12-22 17:50:51', 34469.40826099, 34671.14551404,
    33952.36713708, 35331.14346752, 0.1025,
    0.5853, 6.0, 'TAKE_PROFIT', 4.85,
    1, '1h', '2026-03-08T18:36:22.476519'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5853,
    pnl_amount = 6.0,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BEE05B3448673636', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2020-12-23 10:00:00', '2020-12-23 21:17:51', 3539.51142407, 3522.41935165,
    3592.60409543, 3451.02363847, 0.1155,
    0.4829, 5.58, 'TAKE_PROFIT', 11.3,
    1, '1h', '2026-03-08T18:36:22.479944'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4829,
    pnl_amount = 5.58,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '97DA12D0DD484C00', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2020-12-27 03:00:00', '2020-12-27 11:30:27', 1019.15284367, 1022.24104786,
    1034.44013632, 993.67402258, 0.0837,
    -0.303, -2.54, 'STOP_LOSS', 8.51,
    0, '1h', '2026-03-08T18:36:22.481492'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.303,
    pnl_amount = -2.54,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '144CBDE432BFEA0A', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2020-12-27 21:00:00', '2020-12-28 00:09:02', 2902.36639022, 2893.72654742,
    2858.83089436, 2974.92554997, 0.0843,
    -0.2977, -2.51, 'TIME_EXIT', 3.15,
    0, '1h', '2026-03-08T18:36:22.480987'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2977,
    pnl_amount = -2.51,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E98AA52D2B4D8AE1', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2020-12-30 19:00:00', '2020-12-31 04:24:00', 4512.77554253, 4499.54541169,
    4445.08390939, 4625.59493109, 0.1016,
    -0.2932, -2.98, 'STOP_LOSS', 9.4,
    0, '1h', '2026-03-08T18:36:22.476576'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2932,
    pnl_amount = -2.98,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '464DDBADAF83878D', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2020-12-30 20:00:00', '2020-12-31 04:16:06', 1532.62163265, 1526.1823592,
    1555.61095714, 1494.30609183, 0.1196,
    0.4201, 5.03, 'TIME_EXIT', 8.27,
    1, '1h', '2026-03-08T18:36:22.476001'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4201,
    pnl_amount = 5.03,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6341750D69CA2675', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2020-12-31 16:00:00', '2020-12-31 18:14:19', 1030.551957, 1036.93359998,
    1015.09367764, 1056.31575592, 0.0948,
    0.6192, 5.87, 'TAKE_PROFIT', 2.24,
    1, '1h', '2026-03-08T18:36:22.482949'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6192,
    pnl_amount = 5.87,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A522932018841C70', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2020-12-31 20:00:00', '2021-01-01 02:15:43', 3442.44326469, 3424.79066231,
    3494.07991366, 3356.38218307, 0.0938,
    0.5128, 4.81, 'TIME_EXIT', 6.26,
    1, '1h', '2026-03-08T18:36:22.478811'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5128,
    pnl_amount = 4.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4ABFA72FBD11EE6C', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2021-01-04 19:00:00', '2021-01-05 06:23:49', 3101.7121629, 3082.49235792,
    3148.23784534, 3024.16935882, 0.0853,
    0.6197, 5.28, 'TIME_EXIT', 11.4,
    1, '1h', '2026-03-08T18:36:22.478754'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6197,
    pnl_amount = 5.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EF56AFB460474828', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-01-07 04:00:00', '2021-01-07 12:35:08', 1116.18325682, 1120.68172674,
    1099.44050797, 1144.08783824, 0.0859,
    0.403, 3.46, 'TIME_EXIT', 8.59,
    1, '1h', '2026-03-08T18:36:22.480741'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.403,
    pnl_amount = 3.46,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2134E8087923D7D9', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-01-09 06:00:00', '2021-01-09 09:39:31', 37183.18217282, 37324.35975063,
    36625.43444023, 38112.76172714, 0.1035,
    0.3797, 3.93, 'TAKE_PROFIT', 3.66,
    1, '1h', '2026-03-08T18:36:22.475934'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3797,
    pnl_amount = 3.93,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '51175BBE574C1392', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-01-09 09:00:00', '2021-01-09 16:52:47', 22833.47492493, 22914.64347033,
    23175.9770488, 22262.63805181, 0.1198,
    -0.3555, -4.26, 'STOP_LOSS', 7.88,
    0, '1h', '2026-03-08T18:36:22.480082'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3555,
    pnl_amount = -4.26,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '01420A44D1D4AC78', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-01-13 10:00:00', '2021-01-13 21:32:48', 1785.7046105, 1793.4107929,
    1758.91904135, 1830.34722577, 0.1009,
    0.4315, 4.36, 'TIME_EXIT', 11.55,
    1, '1h', '2026-03-08T18:36:22.482076'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4315,
    pnl_amount = 4.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E13C4178F966FFE9', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2021-01-14 03:00:00', '2021-01-14 08:05:45', 1974.49689795, 1983.69290611,
    1944.87944448, 2023.85932039, 0.1025,
    0.4657, 4.77, 'TIME_EXIT', 5.1,
    1, '1h', '2026-03-08T18:36:22.483644'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4657,
    pnl_amount = 4.77,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '03CE1C8B236EBBE8', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-01-14 11:00:00', '2021-01-14 18:32:02', 33363.79833665, 33157.69081257,
    33864.2553117, 32529.70337824, 0.117,
    0.6178, 7.23, 'TAKE_PROFIT', 7.53,
    1, '1h', '2026-03-08T18:36:22.478906'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6178,
    pnl_amount = 7.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '988320A3CC3CBC0F', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2021-01-17 14:00:00', '2021-01-17 20:30:42', 3936.83391347, 3916.14433678,
    3995.88642217, 3838.41306563, 0.1048,
    0.5255, 5.51, 'TIME_EXIT', 6.51,
    1, '1h', '2026-03-08T18:36:22.480855'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5255,
    pnl_amount = 5.51,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6BB6025A2306D1C7', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2021-01-17 21:00:00', '2021-01-18 06:20:34', 1763.41271091, 1751.70065386,
    1789.86390157, 1719.32739314, 0.1072,
    0.6642, 7.12, 'TRAILING_STOP', 9.34,
    1, '1h', '2026-03-08T18:36:22.477373'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6642,
    pnl_amount = 7.12,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '42451B7A9D7CBCF5', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2021-01-18 14:00:00', '2021-01-18 19:31:48', 1438.62077577, 1442.62912417,
    1460.20008741, 1402.65525638, 0.0996,
    -0.2786, -2.77, 'STOP_LOSS', 5.53,
    0, '1h', '2026-03-08T18:36:22.476276'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2786,
    pnl_amount = -2.77,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4A73249D46A1A5E2', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2021-01-21 19:00:00', '2021-01-22 01:08:25', 3606.64871872, 3627.76454946,
    3552.54898794, 3696.81493669, 0.1141,
    0.5855, 6.68, 'TRAILING_STOP', 6.14,
    1, '1h', '2026-03-08T18:36:22.483635'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5855,
    pnl_amount = 6.68,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '508B717D0F671A93', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-01-23 14:00:00', '2021-01-24 01:52:56', 2873.46767409, 2890.74206068,
    2830.36565898, 2945.30436594, 0.1145,
    0.6012, 6.88, 'TAKE_PROFIT', 11.88,
    1, '1h', '2026-03-08T18:36:22.483057'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6012,
    pnl_amount = 6.88,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9CBB4401ED6EE661', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2021-01-24 00:00:00', '2021-01-24 06:09:12', 2297.84525453, 2291.33674214,
    2263.37757571, 2355.29138589, 0.1095,
    -0.2832, -3.1, 'TIME_EXIT', 6.15,
    0, '1h', '2026-03-08T18:36:22.478225'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2832,
    pnl_amount = -3.1,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B0694DA18F49796D', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-01-24 21:00:00', '2021-01-25 00:44:24', 4681.06502878, 4658.62749888,
    4751.28100422, 4564.03840306, 0.1047,
    0.4793, 5.02, 'TAKE_PROFIT', 3.74,
    1, '1h', '2026-03-08T18:36:22.479480'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4793,
    pnl_amount = 5.02,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '59F3E63C19542293', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2021-01-29 06:00:00', '2021-01-29 16:15:26', 1239.85223864, 1233.31154603,
    1258.45002222, 1208.85593268, 0.0838,
    0.5275, 4.42, 'TRAILING_STOP', 10.26,
    1, '1h', '2026-03-08T18:36:22.478076'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5275,
    pnl_amount = 4.42,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0227472C3B121C4B', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-01-31 16:00:00', '2021-01-31 22:53:12', 2504.35505664, 2496.78922078,
    2466.78973079, 2566.96393305, 0.0956,
    -0.3021, -2.89, 'STOP_LOSS', 6.89,
    0, '1h', '2026-03-08T18:36:22.481349'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3021,
    pnl_amount = -2.89,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4389A4D403A3482C', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2021-02-01 16:00:00', '2021-02-02 01:28:49', 2193.47873606, 2204.33263026,
    2160.57655501, 2248.31570446, 0.0861,
    0.4948, 4.26, 'TRAILING_STOP', 9.48,
    1, '1h', '2026-03-08T18:36:22.476792'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4948,
    pnl_amount = 4.26,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3676483DECBD90D7', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2021-02-01 18:00:00', '2021-02-01 21:47:58', 1744.24816919, 1751.2291997,
    1718.08444666, 1787.85437342, 0.0823,
    0.4002, 3.29, 'TRAILING_STOP', 3.8,
    1, '1h', '2026-03-08T18:36:22.479620'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4002,
    pnl_amount = 3.29,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30330CEC963EB4DA', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2021-02-01 20:00:00', '2021-02-01 22:15:01', 4379.19028644, 4362.92919969,
    4313.50243214, 4488.6700436, 0.1069,
    -0.3713, -3.97, 'TIME_EXIT', 2.25,
    0, '1h', '2026-03-08T18:36:22.480806'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3713,
    pnl_amount = -3.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ADA2BF581F0F19BB', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2021-02-05 22:00:00', '2021-02-06 03:42:00', 1101.38450295, 1097.3612575,
    1117.90527049, 1073.84989037, 0.0851,
    0.3653, 3.11, 'TIME_EXIT', 5.7,
    1, '1h', '2026-03-08T18:36:22.483126'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3653,
    pnl_amount = 3.11,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '12CC01BE5842270D', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-02-07 13:00:00', '2021-02-08 00:28:20', 33822.4169023, 34049.38978281,
    33315.08064876, 34667.97732486, 0.1007,
    0.6711, 6.76, 'TRAILING_STOP', 11.47,
    1, '1h', '2026-03-08T18:36:22.481647'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6711,
    pnl_amount = 6.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '075B9296D48A5BCC', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2021-02-08 13:00:00', '2021-02-08 20:51:46', 456.95510316, 455.28752505,
    463.80942971, 445.53122558, 0.0808,
    0.3649, 2.95, 'TAKE_PROFIT', 7.86,
    1, '1h', '2026-03-08T18:36:22.482417'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3649,
    pnl_amount = 2.95,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2A26830D7342E62A', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-02-08 23:00:00', '2021-02-09 07:09:21', 2089.79380816, 2098.2442169,
    2058.44690104, 2142.03865336, 0.0901,
    0.4044, 3.64, 'TRAILING_STOP', 8.16,
    1, '1h', '2026-03-08T18:36:22.475711'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4044,
    pnl_amount = 3.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F4B80FA2978CC70', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2021-02-11 11:00:00', '2021-02-11 14:52:09', 1837.37177029, 1832.01793969,
    1809.81119373, 1883.30606454, 0.1125,
    -0.2914, -3.28, 'TIME_EXIT', 3.87,
    0, '1h', '2026-03-08T18:36:22.480864'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2914,
    pnl_amount = -3.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '44F636ECA8CA1878', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2021-02-15 12:00:00', '2021-02-15 14:08:57', 3941.45096726, 3915.05526542,
    4000.57273177, 3842.91469308, 0.086,
    0.6697, 5.76, 'TIME_EXIT', 2.15,
    1, '1h', '2026-03-08T18:36:22.478345'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6697,
    pnl_amount = 5.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CB46B93E1A986A7F', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2021-02-16 00:00:00', '2021-02-16 03:44:06', 3886.23712516, 3897.33578766,
    3944.53068204, 3789.08119703, 0.0832,
    -0.2856, -2.37, 'STOP_LOSS', 3.74,
    0, '1h', '2026-03-08T18:36:22.477923'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2856,
    pnl_amount = -2.37,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '896C4C5FCC0E8759', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2021-02-16 10:00:00', '2021-02-16 20:43:42', 2908.99039105, 2926.10655657,
    2865.35553519, 2981.71515083, 0.1037,
    0.5884, 6.1, 'TRAILING_STOP', 10.73,
    1, '1h', '2026-03-08T18:36:22.479517'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5884,
    pnl_amount = 6.1,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30B9B76AD20A9543', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2021-02-16 15:00:00', '2021-02-16 23:43:33', 3305.27288825, 3293.24027383,
    3354.85198157, 3222.64106604, 0.1032,
    0.364, 3.76, 'TRAILING_STOP', 8.73,
    1, '1h', '2026-03-08T18:36:22.476567'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.364,
    pnl_amount = 3.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DBE29E16437C5FDB', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2021-02-18 08:00:00', '2021-02-18 11:30:26', 3796.93434502, 3774.43826367,
    3853.88836019, 3702.01098639, 0.1154,
    0.5925, 6.84, 'TAKE_PROFIT', 3.51,
    1, '1h', '2026-03-08T18:36:22.481533'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5925,
    pnl_amount = 6.84,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '40072DC5A0621C04', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2021-02-19 06:00:00', '2021-02-19 10:37:27', 2505.87280549, 2497.32647088,
    2468.28471341, 2568.51962563, 0.1152,
    -0.3411, -3.93, 'STOP_LOSS', 4.62,
    0, '1h', '2026-03-08T18:36:22.481749'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3411,
    pnl_amount = -3.93,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '35E06E6ABC873175', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-02-21 20:00:00', '2021-02-22 02:51:26', 2807.37179712, 2815.61827167,
    2849.48237407, 2737.18750219, 0.0979,
    -0.2937, -2.88, 'TIME_EXIT', 6.86,
    0, '1h', '2026-03-08T18:36:22.483485'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2937,
    pnl_amount = -2.88,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0023B4C9BE4ADB01', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-02-22 21:00:00', '2021-02-23 02:46:05', 764.32665557, 768.77741458,
    752.86175573, 783.43482195, 0.0917,
    0.5823, 5.34, 'TIME_EXIT', 5.77,
    1, '1h', '2026-03-08T18:36:22.476773'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5823,
    pnl_amount = 5.34,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B1DFBF6B9A30045F', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-02-24 00:00:00', '2021-02-24 02:26:37', 1583.69165366, 1590.10830952,
    1559.93627886, 1623.28394501, 0.1111,
    0.4052, 4.5, 'TIME_EXIT', 2.44,
    1, '1h', '2026-03-08T18:36:22.477960'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4052,
    pnl_amount = 4.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '41D932DDF3C284CB', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-02-24 12:00:00', '2021-02-24 16:45:49', 3557.37872658, 3568.31661137,
    3610.73940748, 3468.44425842, 0.0861,
    -0.3075, -2.65, 'STOP_LOSS', 4.76,
    0, '1h', '2026-03-08T18:36:22.482225'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3075,
    pnl_amount = -2.65,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '88C780D07E8CE1EA', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2021-02-27 15:00:00', '2021-02-28 02:57:28', 3786.58209235, 3800.52998959,
    3729.78336097, 3881.24664466, 0.091,
    0.3684, 3.35, 'TRAILING_STOP', 11.96,
    1, '1h', '2026-03-08T18:36:22.478006'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3684,
    pnl_amount = 3.35,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A17CA68EAA5F0413', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-02-28 02:00:00', '2021-02-28 07:59:11', 501.29150054, 499.97645096,
    493.77212803, 513.82378805, 0.0852,
    -0.2623, -2.24, 'STOP_LOSS', 5.99,
    0, '1h', '2026-03-08T18:36:22.479286'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2623,
    pnl_amount = -2.24,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '20C844452A714588', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2021-03-01 16:00:00', '2021-03-01 19:00:30', 2755.8885661, 2745.41591064,
    2797.22689459, 2686.99135195, 0.0834,
    0.38, 3.17, 'TIME_EXIT', 3.01,
    1, '1h', '2026-03-08T18:36:22.479063'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.38,
    pnl_amount = 3.17,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1C4184001E0B3F0F', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-03-05 14:00:00', '2021-03-05 22:32:29', 455.70911867, 454.08134942,
    448.87348189, 467.10184663, 0.1142,
    -0.3572, -4.08, 'TIME_EXIT', 8.54,
    0, '1h', '2026-03-08T18:36:22.481084'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3572,
    pnl_amount = -4.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A314DE4114352EDB', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2021-03-07 17:00:00', '2021-03-08 01:35:53', 1366.41640205, 1359.27412614,
    1386.91264808, 1332.255992, 0.1137,
    0.5227, 5.94, 'TRAILING_STOP', 8.6,
    1, '1h', '2026-03-08T18:36:22.481427'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5227,
    pnl_amount = 5.94,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75C0CC99A88438EB', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-03-07 18:00:00', '2021-03-07 23:45:00', 1066.74083862, 1073.06860658,
    1050.73972604, 1093.40935958, 0.0867,
    0.5932, 5.14, 'TRAILING_STOP', 5.75,
    1, '1h', '2026-03-08T18:36:22.476221'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5932,
    pnl_amount = 5.14,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F852B3DBF250EFA', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2021-03-08 05:00:00', '2021-03-08 16:19:18', 4446.72494091, 4430.26174919,
    4513.42581502, 4335.55681738, 0.0874,
    0.3702, 3.24, 'TAKE_PROFIT', 11.32,
    1, '1h', '2026-03-08T18:36:22.482995'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3702,
    pnl_amount = 3.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '720D4852279C16DB', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-03-11 14:00:00', '2021-03-11 17:07:27', 1857.38069132, 1851.48677175,
    1829.51998095, 1903.8152086, 0.0857,
    -0.3173, -2.72, 'STOP_LOSS', 3.12,
    0, '1h', '2026-03-08T18:36:22.479489'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3173,
    pnl_amount = -2.72,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1AAE94B276F58C52', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2021-03-14 16:00:00', '2021-03-14 21:55:01', 1726.70734311, 1717.51448202,
    1752.60795326, 1683.53965953, 0.1021,
    0.5324, 5.43, 'TRAILING_STOP', 5.92,
    1, '1h', '2026-03-08T18:36:22.478977'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5324,
    pnl_amount = 5.43,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '76621718AA287006', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-03-27 00:00:00', '2021-03-27 08:58:47', 2418.59851762, 2432.51683182,
    2382.31953986, 2479.06348056, 0.1101,
    0.5755, 6.34, 'TIME_EXIT', 8.98,
    1, '1h', '2026-03-08T18:36:22.483013'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5755,
    pnl_amount = 6.34,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1B05D7D3E3E22242', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2021-03-28 19:00:00', '2021-03-29 06:40:38', 2245.73425949, 2230.39670446,
    2279.42027338, 2189.590903, 0.0836,
    0.683, 5.71, 'TAKE_PROFIT', 11.68,
    1, '1h', '2026-03-08T18:36:22.480198'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.683,
    pnl_amount = 5.71,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '50F5A3981C0F70F3', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-03-29 13:00:00', '2021-03-29 20:40:15', 46750.58389483, 46433.2346726,
    47451.84265325, 45581.81929746, 0.0932,
    0.6788, 6.33, 'TRAILING_STOP', 7.67,
    1, '1h', '2026-03-08T18:36:22.477542'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6788,
    pnl_amount = 6.33,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FE7043F1FA66D2D1', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2021-03-31 16:00:00', '2021-04-01 02:43:33', 1653.38010821, 1642.00362206,
    1678.18080983, 1612.0456055, 0.0842,
    0.6881, 5.79, 'TIME_EXIT', 10.73,
    1, '1h', '2026-03-08T18:36:22.483346'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6881,
    pnl_amount = 5.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DC130DBE07F0F0C0', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2021-04-03 23:00:00', '2021-04-04 07:16:38', 1299.85606675, 1296.51696673,
    1280.35822575, 1332.35246842, 0.1076,
    -0.2569, -2.76, 'STOP_LOSS', 8.28,
    0, '1h', '2026-03-08T18:36:22.478567'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2569,
    pnl_amount = -2.76,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '94EF6A29508267ED', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2021-04-08 20:00:00', '2021-04-09 06:17:05', 841.45073775, 839.06268217,
    828.82897668, 862.48700619, 0.0934,
    -0.2838, -2.65, 'TIME_EXIT', 10.28,
    0, '1h', '2026-03-08T18:36:22.478802'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2838,
    pnl_amount = -2.65,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '443BBD27423D4AA7', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2021-04-13 11:00:00', '2021-04-13 21:43:16', 1798.23667302, 1807.75146186,
    1771.26312292, 1843.19258984, 0.1116,
    0.5291, 5.9, 'TRAILING_STOP', 10.72,
    1, '1h', '2026-03-08T18:36:22.481399'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5291,
    pnl_amount = 5.9,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A429C21B1C22AE21', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-04-13 19:00:00', '2021-04-14 03:14:38', 1948.01574303, 1961.6493694,
    1918.79550688, 1996.71613661, 0.0947,
    0.6999, 6.63, 'TIME_EXIT', 8.24,
    1, '1h', '2026-03-08T18:36:22.480930'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6999,
    pnl_amount = 6.63,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '91D078B11B8921E8', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2021-04-13 20:00:00', '2021-04-14 07:41:44', 1553.74165401, 1559.11232074,
    1577.04777882, 1514.89811266, 0.0976,
    -0.3457, -3.37, 'STOP_LOSS', 11.7,
    0, '1h', '2026-03-08T18:36:22.477941'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3457,
    pnl_amount = -3.37,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E79FAB237AC9C31B', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2021-04-14 07:00:00', '2021-04-14 09:02:34', 4768.20161469, 4791.55098721,
    4696.67859047, 4887.40665506, 0.1148,
    0.4897, 5.62, 'TIME_EXIT', 2.04,
    1, '1h', '2026-03-08T18:36:22.483710'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4897,
    pnl_amount = 5.62,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C63C9301733A328E', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-04-16 17:00:00', '2021-04-16 22:03:13', 40264.55474128, 40389.56610718,
    40868.5230624, 39257.94087275, 0.0944,
    -0.3105, -2.93, 'TIME_EXIT', 5.05,
    0, '1h', '2026-03-08T18:36:22.476530'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3105,
    pnl_amount = -2.93,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E74355399CA00BEB', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2021-04-16 18:00:00', '2021-04-17 02:52:48', 346.35771225, 344.64241373,
    351.55307793, 337.69876944, 0.1129,
    0.4952, 5.59, 'TIME_EXIT', 8.88,
    1, '1h', '2026-03-08T18:36:22.482702'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4952,
    pnl_amount = 5.59,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '73F42A0466B777E1', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2021-04-17 06:00:00', '2021-04-17 09:56:12', 3241.07202525, 3258.45733107,
    3192.45594487, 3322.09882588, 0.1084,
    0.5364, 5.82, 'TIME_EXIT', 3.94,
    1, '1h', '2026-03-08T18:36:22.480668'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5364,
    pnl_amount = 5.82,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A07FF097CC02DE2C', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2021-04-18 19:00:00', '2021-04-19 04:06:50', 615.68154432, 613.41434428,
    606.44632116, 631.07358293, 0.1184,
    -0.3682, -4.36, 'STOP_LOSS', 9.11,
    0, '1h', '2026-03-08T18:36:22.483293'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3682,
    pnl_amount = -4.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96A623A62643076C', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2021-04-22 06:00:00', '2021-04-22 15:36:04', 3932.94906733, 3916.8445465,
    3991.94330333, 3834.62534064, 0.0883,
    0.4095, 3.62, 'TRAILING_STOP', 9.6,
    1, '1h', '2026-03-08T18:36:22.481701'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4095,
    pnl_amount = 3.62,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '174F4560BDF0AC76', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2021-04-24 14:00:00', '2021-04-25 00:51:45', 4974.13884314, 4956.16512415,
    4899.52676049, 5098.49231421, 0.1183,
    -0.3613, -4.27, 'STOP_LOSS', 10.86,
    0, '1h', '2026-03-08T18:36:22.477085'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3613,
    pnl_amount = -4.27,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '70799994FCE1EFA3', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-04-25 09:00:00', '2021-04-25 16:04:50', 2668.14517246, 2661.15424127,
    2628.12299488, 2734.84880177, 0.0821,
    -0.262, -2.15, 'STOP_LOSS', 7.08,
    0, '1h', '2026-03-08T18:36:22.479851'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.262,
    pnl_amount = -2.15,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '26A752E7570B8F6A', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-05-02 14:00:00', '2021-05-02 18:43:13', 2734.37083146, 2749.64899234,
    2693.35526899, 2802.73010225, 0.1078,
    0.5587, 6.02, 'TIME_EXIT', 4.72,
    1, '1h', '2026-03-08T18:36:22.482929'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5587,
    pnl_amount = 6.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '53AB3BAB2D3C678E', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2021-05-03 00:00:00', '2021-05-03 02:56:46', 3352.38686667, 3336.15047498,
    3402.67266967, 3268.577195, 0.0899,
    0.4843, 4.35, 'TAKE_PROFIT', 2.95,
    1, '1h', '2026-03-08T18:36:22.477821'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4843,
    pnl_amount = 4.35,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A73CD257901FE623', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-05-03 23:00:00', '2021-05-04 10:24:44', 29053.82749431, 29132.91884393,
    29489.63490672, 28327.48180695, 0.0871,
    -0.2722, -2.37, 'STOP_LOSS', 11.41,
    0, '1h', '2026-03-08T18:36:22.484050'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2722,
    pnl_amount = -2.37,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C1DC6EEA5F0CDE9A', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2021-05-05 02:00:00', '2021-05-05 09:26:15', 3603.39305313, 3616.32593985,
    3549.34215733, 3693.47787945, 0.0985,
    0.3589, 3.54, 'TRAILING_STOP', 7.44,
    1, '1h', '2026-03-08T18:36:22.479090'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3589,
    pnl_amount = 3.54,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B33EEFD97F6B1663', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-05-06 22:00:00', '2021-05-07 01:45:10', 2726.92699013, 2713.98062184,
    2767.83089499, 2658.75381538, 0.1131,
    0.4748, 5.37, 'TAKE_PROFIT', 3.75,
    1, '1h', '2026-03-08T18:36:22.479683'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4748,
    pnl_amount = 5.37,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6B036DE1E6E543AD', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-05-08 22:00:00', '2021-05-09 08:57:58', 3291.63328684, 3280.29974179,
    3242.25878753, 3373.92411901, 0.1143,
    -0.3443, -3.93, 'TIME_EXIT', 10.97,
    0, '1h', '2026-03-08T18:36:22.483918'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3443,
    pnl_amount = -3.93,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '62AB7FADA7DBFA97', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-05-15 07:00:00', '2021-05-15 18:35:02', 469.43903332, 472.37976192,
    462.39744782, 481.17500915, 0.0857,
    0.6264, 5.37, 'TIME_EXIT', 11.58,
    1, '1h', '2026-03-08T18:36:22.475735'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6264,
    pnl_amount = 5.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0439D742ED43CAE1', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2021-05-21 01:00:00', '2021-05-21 12:21:27', 3644.75747046, 3622.86574686,
    3699.42883251, 3553.6385337, 0.0814,
    0.6006, 4.89, 'TRAILING_STOP', 11.36,
    1, '1h', '2026-03-08T18:36:22.481710'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6006,
    pnl_amount = 4.89,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C2C6D5E75EB07807', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-05-26 12:00:00', '2021-05-26 22:29:58', 4268.55947842, 4257.63056233,
    4204.53108624, 4375.27346538, 0.0995,
    -0.256, -2.55, 'TIME_EXIT', 10.5,
    0, '1h', '2026-03-08T18:36:22.481438'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.256,
    pnl_amount = -2.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '977EBE625F34F0B3', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2021-05-26 21:00:00', '2021-05-27 07:33:47', 3852.60465196, 3830.35695504,
    3910.39372174, 3756.28953566, 0.1042,
    0.5775, 6.01, 'TRAILING_STOP', 10.56,
    1, '1h', '2026-03-08T18:36:22.483031'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5775,
    pnl_amount = 6.01,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9457430DBE209E4B', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2021-05-27 05:00:00', '2021-05-27 15:50:49', 936.60665325, 939.30804957,
    950.65575305, 913.19148692, 0.0894,
    -0.2884, -2.58, 'STOP_LOSS', 10.85,
    0, '1h', '2026-03-08T18:36:22.480252'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2884,
    pnl_amount = -2.58,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F34594289252A364', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-05-28 12:00:00', '2021-05-28 18:42:50', 10234.0338576, 10277.80530258,
    10080.52334973, 10489.88470404, 0.0898,
    0.4277, 3.84, 'TIME_EXIT', 6.71,
    1, '1h', '2026-03-08T18:36:22.482297'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4277,
    pnl_amount = 3.84,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F774DDD1F656CE5A', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2021-05-30 17:00:00', '2021-05-31 03:24:39', 1302.30136146, 1298.79664973,
    1282.76684103, 1334.85889549, 0.1165,
    -0.2691, -3.14, 'TIME_EXIT', 10.41,
    0, '1h', '2026-03-08T18:36:22.482307'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2691,
    pnl_amount = -3.14,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F2FBD711C1C9074C', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2021-06-01 23:00:00', '2021-06-02 05:44:41', 1782.01397161, 1773.75678503,
    1808.74418118, 1737.46362232, 0.102,
    0.4634, 4.73, 'TAKE_PROFIT', 6.74,
    1, '1h', '2026-03-08T18:36:22.480534'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4634,
    pnl_amount = 4.73,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B80D173855972A08', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2021-06-04 09:00:00', '2021-06-04 11:23:36', 2081.13794651, 2088.59231038,
    2112.35501571, 2029.10949785, 0.0982,
    -0.3582, -3.52, 'STOP_LOSS', 2.39,
    0, '1h', '2026-03-08T18:36:22.480939'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3582,
    pnl_amount = -3.52,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '49E7AC679CD6B1BF', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-06-04 15:00:00', '2021-06-05 01:37:52', 6274.26279842, 6251.38890755,
    6180.14885644, 6431.11936838, 0.0928,
    -0.3646, -3.38, 'TIME_EXIT', 10.63,
    0, '1h', '2026-03-08T18:36:22.480713'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3646,
    pnl_amount = -3.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B09C4357BD3EEBCF', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-06-06 00:00:00', '2021-06-06 03:35:57', 28329.11722398, 28479.74956528,
    27904.18046562, 29037.34515458, 0.1125,
    0.5317, 5.98, 'TIME_EXIT', 3.6,
    1, '1h', '2026-03-08T18:36:22.476322'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5317,
    pnl_amount = 5.98,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96BAB3F6423ACD59', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-06-06 18:00:00', '2021-06-06 20:24:15', 3496.09420267, 3485.1303956,
    3443.65278963, 3583.49655774, 0.081,
    -0.3136, -2.54, 'TIME_EXIT', 2.4,
    0, '1h', '2026-03-08T18:36:22.476829'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3136,
    pnl_amount = -2.54,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4FB0878C27F91F20', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-06-08 13:00:00', '2021-06-09 00:12:18', 2249.13534361, 2234.45624841,
    2282.87237377, 2192.90696002, 0.1054,
    0.6527, 6.88, 'TAKE_PROFIT', 11.21,
    1, '1h', '2026-03-08T18:36:22.478548'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6527,
    pnl_amount = 6.88,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '69C600A771E8637B', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-06-11 21:00:00', '2021-06-12 07:18:15', 45499.68424268, 45181.49440037,
    46182.17950632, 44362.19213661, 0.0874,
    0.6993, 6.11, 'TIME_EXIT', 10.3,
    1, '1h', '2026-03-08T18:36:22.482288'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6993,
    pnl_amount = 6.11,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '24EBB8B4DB65320F', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2021-06-13 23:00:00', '2021-06-14 04:35:23', 163.39558593, 163.86281794,
    165.84651972, 159.31069628, 0.114,
    -0.286, -3.26, 'TIME_EXIT', 5.59,
    0, '1h', '2026-03-08T18:36:22.476754'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.286,
    pnl_amount = -3.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DBAC31512371C3D8', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-06-17 22:00:00', '2021-06-18 05:13:18', 1023.01398478, 1020.26222819,
    1007.66877501, 1048.5893344, 0.096,
    -0.269, -2.58, 'TIME_EXIT', 7.22,
    0, '1h', '2026-03-08T18:36:22.480948'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.269,
    pnl_amount = -2.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98D1726CECE67F8B', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-06-21 15:00:00', '2021-06-21 19:00:40', 33342.26296032, 33176.94314935,
    33842.39690472, 32508.70638631, 0.0933,
    0.4958, 4.63, 'TIME_EXIT', 4.01,
    1, '1h', '2026-03-08T18:36:22.478925'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4958,
    pnl_amount = 4.63,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0B90FDCE4727861D', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2021-06-29 00:00:00', '2021-06-29 03:53:21', 65.7650866, 65.53472254,
    66.7515629, 64.12095944, 0.1007,
    0.3503, 3.53, 'TRAILING_STOP', 3.89,
    1, '1h', '2026-03-08T18:36:22.478688'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3503,
    pnl_amount = 3.53,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '897D952A51F9B4A4', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-06-29 06:00:00', '2021-06-29 09:01:38', 26452.24098862, 26589.11845933,
    26055.45737379, 27113.54701334, 0.0855,
    0.5175, 4.42, 'TAKE_PROFIT', 3.03,
    1, '1h', '2026-03-08T18:36:22.480225'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5175,
    pnl_amount = 4.42,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '20AD259F2DEF3414', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-07-01 08:00:00', '2021-07-01 16:43:22', 1189.11158027, 1196.37858821,
    1171.27490656, 1218.83936977, 0.1177,
    0.6111, 7.19, 'TIME_EXIT', 8.72,
    1, '1h', '2026-03-08T18:36:22.480788'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6111,
    pnl_amount = 7.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C5C41AC3CF9852BF', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-07-02 07:00:00', '2021-07-02 16:39:56', 4973.062463, 4940.97226628,
    5047.65839994, 4848.73590142, 0.1156,
    0.6453, 7.46, 'TAKE_PROFIT', 9.67,
    1, '1h', '2026-03-08T18:36:22.478401'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6453,
    pnl_amount = 7.46,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '689200C0793938B6', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-07-05 05:00:00', '2021-07-05 07:41:47', 3508.55948946, 3488.71222309,
    3561.1878818, 3420.84550222, 0.1096,
    0.5657, 6.2, 'TRAILING_STOP', 2.7,
    1, '1h', '2026-03-08T18:36:22.475699'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5657,
    pnl_amount = 6.2,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '120ECB0A4B688F6A', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2021-07-05 19:00:00', '2021-07-06 02:08:56', 3284.56194892, 3303.23747141,
    3235.29351968, 3366.67599764, 0.1193,
    0.5686, 6.79, 'TIME_EXIT', 7.15,
    1, '1h', '2026-03-08T18:36:22.478185'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5686,
    pnl_amount = 6.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6658A7063227E30A', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2021-07-07 15:00:00', '2021-07-07 18:06:56', 2626.89747996, 2645.0073712,
    2587.49401776, 2692.56991696, 0.0956,
    0.6894, 6.59, 'TAKE_PROFIT', 3.12,
    1, '1h', '2026-03-08T18:36:22.479303'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6894,
    pnl_amount = 6.59,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '675E0904D2FB6673', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-07-08 07:00:00', '2021-07-08 12:47:31', 1159.98003697, 1152.06302332,
    1177.37973752, 1130.98053604, 0.0967,
    0.6825, 6.6, 'TAKE_PROFIT', 5.79,
    1, '1h', '2026-03-08T18:36:22.478476'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6825,
    pnl_amount = 6.6,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0EEC6C4584AA2FF4', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-07-08 08:00:00', '2021-07-08 16:35:28', 2854.11434529, 2865.89884805,
    2811.30263011, 2925.46720392, 0.1054,
    0.4129, 4.35, 'TIME_EXIT', 8.59,
    1, '1h', '2026-03-08T18:36:22.476846'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4129,
    pnl_amount = 4.35,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6FDB61813FF7A22D', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2021-07-12 14:00:00', '2021-07-12 22:46:35', 4323.89603045, 4338.57243442,
    4388.75447091, 4215.79862969, 0.1028,
    -0.3394, -3.49, 'TIME_EXIT', 8.78,
    0, '1h', '2026-03-08T18:36:22.476400'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3394,
    pnl_amount = -3.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D2B60BFA1938D558', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2021-07-14 13:00:00', '2021-07-15 00:47:43', 2901.95255012, 2916.35460607,
    2858.42326187, 2974.50136387, 0.1078,
    0.4963, 5.35, 'TAKE_PROFIT', 11.8,
    1, '1h', '2026-03-08T18:36:22.481998'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4963,
    pnl_amount = 5.35,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0CEDE86D363A64E8', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-07-15 01:00:00', '2021-07-15 09:24:49', 2025.76021986, 2015.98930154,
    2056.14662316, 1975.11621436, 0.0805,
    0.4823, 3.88, 'TRAILING_STOP', 8.41,
    1, '1h', '2026-03-08T18:36:22.479277'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4823,
    pnl_amount = 3.88,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E9ADB89B979AE3C2', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2021-07-17 07:00:00', '2021-07-17 12:52:14', 3254.2235163, 3243.31230318,
    3205.41016356, 3335.57910421, 0.0982,
    -0.3353, -3.29, 'STOP_LOSS', 5.87,
    0, '1h', '2026-03-08T18:36:22.476285'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3353,
    pnl_amount = -3.29,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BFFD12D63B083C54', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-07-21 14:00:00', '2021-07-21 21:52:13', 3271.52408326, 3261.64871025,
    3222.45122201, 3353.31218534, 0.0822,
    -0.3019, -2.48, 'TIME_EXIT', 7.87,
    0, '1h', '2026-03-08T18:36:22.482123'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3019,
    pnl_amount = -2.48,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D3B8085ADA9D6C03', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-07-24 11:00:00', '2021-07-24 15:06:46', 2962.49033609, 2952.16094321,
    2918.05298105, 3036.55259449, 0.0974,
    -0.3487, -3.4, 'TIME_EXIT', 4.11,
    0, '1h', '2026-03-08T18:36:22.478783'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3487,
    pnl_amount = -3.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96F4E1B204207F07', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-07-26 03:00:00', '2021-07-26 09:02:28', 1698.66762456, 1687.27325478,
    1724.14763893, 1656.20093394, 0.0956,
    0.6708, 6.42, 'TAKE_PROFIT', 6.04,
    1, '1h', '2026-03-08T18:36:22.478763'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6708,
    pnl_amount = 6.42,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '24D8EB3A94E68CE7', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2021-07-27 02:00:00', '2021-07-27 08:25:29', 1041.8708953, 1034.67297754,
    1057.49895873, 1015.82412292, 0.0849,
    0.6909, 5.86, 'TRAILING_STOP', 6.42,
    1, '1h', '2026-03-08T18:36:22.478579'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6909,
    pnl_amount = 5.86,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '76F7F2F671EFEDB8', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2021-07-28 14:00:00', '2021-07-28 16:44:20', 3462.22402212, 3443.1541259,
    3514.15738245, 3375.66842156, 0.1071,
    0.5508, 5.9, 'TAKE_PROFIT', 2.74,
    1, '1h', '2026-03-08T18:36:22.477533'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5508,
    pnl_amount = 5.9,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '24B11CE0785E92F5', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-07-31 08:00:00', '2021-07-31 19:00:18', 4465.210115, 4446.145401,
    4532.18826673, 4353.57986213, 0.0834,
    0.427, 3.56, 'TRAILING_STOP', 11.01,
    1, '1h', '2026-03-08T18:36:22.477177'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.427,
    pnl_amount = 3.56,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '22AF206A65A91EA6', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-08-04 14:00:00', '2021-08-04 23:00:11', 2734.57391665, 2726.90851838,
    2693.5553079, 2802.93826457, 0.1113,
    -0.2803, -3.12, 'STOP_LOSS', 9.0,
    0, '1h', '2026-03-08T18:36:22.475992'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2803,
    pnl_amount = -3.12,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FB2560A176ECAAFB', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2021-08-05 15:00:00', '2021-08-05 19:36:36', 3261.99488643, 3270.98729369,
    3310.92480973, 3180.44501427, 0.118,
    -0.2757, -3.25, 'TIME_EXIT', 4.61,
    0, '1h', '2026-03-08T18:36:22.484010'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2757,
    pnl_amount = -3.25,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6D01FFC1AAB5CA93', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-08-06 08:00:00', '2021-08-06 15:49:45', 4733.21715533, 4705.29882747,
    4804.21541266, 4614.88672645, 0.0891,
    0.5898, 5.26, 'TIME_EXIT', 7.83,
    1, '1h', '2026-03-08T18:36:22.480515'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5898,
    pnl_amount = 5.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '64C6112498A6C9EB', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-08-09 03:00:00', '2021-08-09 08:07:40', 4863.69299645, 4840.39761397,
    4936.6483914, 4742.10067154, 0.0893,
    0.479, 4.28, 'TIME_EXIT', 5.13,
    1, '1h', '2026-03-08T18:36:22.483171'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.479,
    pnl_amount = 4.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5B998043B1536D1A', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2021-08-10 19:00:00', '2021-08-10 21:50:25', 910.73062531, 915.10117936,
    897.06966593, 933.49889094, 0.0822,
    0.4799, 3.94, 'TAKE_PROFIT', 2.84,
    1, '1h', '2026-03-08T18:36:22.482489'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4799,
    pnl_amount = 3.94,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5093BFE2555366CC', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-08-12 21:00:00', '2021-08-13 07:40:34', 3537.4517135, 3526.94433082,
    3484.3899378, 3625.88800634, 0.0853,
    -0.297, -2.53, 'STOP_LOSS', 10.68,
    0, '1h', '2026-03-08T18:36:22.483981'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.297,
    pnl_amount = -2.53,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '46CC70DE813ADA5E', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-08-17 21:00:00', '2021-08-18 02:51:50', 2318.32445137, 2325.42225429,
    2353.09931814, 2260.36634008, 0.1093,
    -0.3062, -3.35, 'STOP_LOSS', 5.86,
    0, '1h', '2026-03-08T18:36:22.481482'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3062,
    pnl_amount = -3.35,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A4E7508A7732BD02', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2021-08-23 21:00:00', '2021-08-23 23:46:18', 4722.19667088, 4742.86636373,
    4651.36372082, 4840.25158765, 0.0853,
    0.4377, 3.73, 'TRAILING_STOP', 2.77,
    1, '1h', '2026-03-08T18:36:22.479159'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4377,
    pnl_amount = 3.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '47EC621FDFAAD0AA', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-08-25 11:00:00', '2021-08-25 22:29:37', 976.50629716, 981.53014876,
    961.8587027, 1000.91895459, 0.0877,
    0.5145, 4.51, 'TIME_EXIT', 11.49,
    1, '1h', '2026-03-08T18:36:22.478067'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5145,
    pnl_amount = 4.51,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EC8AE8C5E1425FF6', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-08-25 20:00:00', '2021-08-26 01:03:09', 29817.91562445, 29921.26751426,
    30265.18435882, 29072.46773384, 0.0891,
    -0.3466, -3.09, 'TIME_EXIT', 5.05,
    0, '1h', '2026-03-08T18:36:22.482535'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3466,
    pnl_amount = -3.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '09C2C752BDECD99B', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2021-08-26 01:00:00', '2021-08-26 04:45:37', 1969.52306132, 1980.21476121,
    1939.9802154, 2018.76113785, 0.0855,
    0.5429, 4.64, 'TRAILING_STOP', 3.76,
    1, '1h', '2026-03-08T18:36:22.483049'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5429,
    pnl_amount = 4.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '604BA15F7BC9B4E0', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2021-08-29 23:00:00', '2021-08-30 07:00:09', 589.91731541, 587.04199411,
    598.76607514, 575.16938252, 0.1049,
    0.4874, 5.11, 'TIME_EXIT', 8.0,
    1, '1h', '2026-03-08T18:36:22.476819'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4874,
    pnl_amount = 5.11,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A94413BFC527E77', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-09-02 23:00:00', '2021-09-03 07:20:31', 3094.3502038, 3078.28071596,
    3140.76545686, 3016.99144871, 0.0851,
    0.5193, 4.42, 'TAKE_PROFIT', 8.34,
    1, '1h', '2026-03-08T18:36:22.476257'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5193,
    pnl_amount = 4.42,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '90153D7951ECB354', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2021-09-03 09:00:00', '2021-09-03 15:41:12', 4329.69613002, 4358.35723147,
    4264.75068807, 4437.93853327, 0.1138,
    0.662, 7.53, 'TIME_EXIT', 6.69,
    1, '1h', '2026-03-08T18:36:22.482729'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.662,
    pnl_amount = 7.53,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '892E2104BF34B520', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-09-09 15:00:00', '2021-09-10 01:43:28', 900.92226917, 897.55175044,
    914.43610321, 878.39921244, 0.1176,
    0.3741, 4.4, 'TRAILING_STOP', 10.72,
    1, '1h', '2026-03-08T18:36:22.483385'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3741,
    pnl_amount = 4.4,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8F460D34975DE16C', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2021-09-13 16:00:00', '2021-09-13 19:22:36', 3164.11246432, 3177.99360706,
    3116.65077736, 3243.21527593, 0.0973,
    0.4387, 4.27, 'TRAILING_STOP', 3.38,
    1, '1h', '2026-03-08T18:36:22.478624'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4387,
    pnl_amount = 4.27,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '01B3A9A530A2D210', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2021-09-19 00:00:00', '2021-09-19 08:09:25', 3795.56862504, 3814.18079462,
    3738.63509566, 3890.45784066, 0.1184,
    0.4904, 5.81, 'TIME_EXIT', 8.16,
    1, '1h', '2026-03-08T18:36:22.477560'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4904,
    pnl_amount = 5.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '23AEE511F6CE64B2', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-09-19 12:00:00', '2021-09-19 22:41:05', 139.48870791, 140.05107555,
    137.39637729, 142.9759256, 0.0812,
    0.4032, 3.27, 'TRAILING_STOP', 10.68,
    1, '1h', '2026-03-08T18:36:22.480441'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4032,
    pnl_amount = 3.27,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C299E7930046256', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2021-09-25 20:00:00', '2021-09-26 00:16:27', 2041.76723023, 2048.7011136,
    2072.39373868, 1990.72304947, 0.0988,
    -0.3396, -3.36, 'STOP_LOSS', 4.27,
    0, '1h', '2026-03-08T18:36:22.479396'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3396,
    pnl_amount = -3.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5C23C738294A7C8D', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-09-27 15:00:00', '2021-09-28 02:56:04', 943.11004115, 938.10427209,
    957.25669177, 919.53229012, 0.0828,
    0.5308, 4.4, 'TRAILING_STOP', 11.93,
    1, '1h', '2026-03-08T18:36:22.475746'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5308,
    pnl_amount = 4.4,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7374A49470E7D12D', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-09-27 20:00:00', '2021-09-28 03:06:07', 2316.46929076, 2324.75797264,
    2351.21633012, 2258.55755849, 0.0966,
    -0.3578, -3.46, 'STOP_LOSS', 7.1,
    0, '1h', '2026-03-08T18:36:22.481814'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3578,
    pnl_amount = -3.46,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7B05C5E52C095895', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2021-09-27 23:00:00', '2021-09-28 08:54:48', 4011.6493337, 3995.24423951,
    4071.82407371, 3911.35810036, 0.098,
    0.4089, 4.01, 'TRAILING_STOP', 9.91,
    1, '1h', '2026-03-08T18:36:22.478147'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4089,
    pnl_amount = 4.01,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D8B8AF0C0B800C5A', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2021-10-05 01:00:00', '2021-10-05 11:05:42', 1874.83337783, 1882.57390029,
    1846.71087716, 1921.70421227, 0.0856,
    0.4129, 3.53, 'TAKE_PROFIT', 10.1,
    1, '1h', '2026-03-08T18:36:22.483680'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4129,
    pnl_amount = 3.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1032E5C037202FA8', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-10-12 12:00:00', '2021-10-12 15:20:40', 41399.58392906, 41201.92465791,
    42020.577688, 40364.59433083, 0.0821,
    0.4774, 3.92, 'TAKE_PROFIT', 3.34,
    1, '1h', '2026-03-08T18:36:22.477895'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4774,
    pnl_amount = 3.92,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '480153DB27ED90AC', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2021-10-15 04:00:00', '2021-10-15 15:41:21', 3068.20504873, 3083.85334093,
    3022.181973, 3144.91017495, 0.0887,
    0.51, 4.53, 'TAKE_PROFIT', 11.69,
    1, '1h', '2026-03-08T18:36:22.476173'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.51,
    pnl_amount = 4.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '387CC89EB5617BD8', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2021-10-16 08:00:00', '2021-10-16 14:13:30', 1279.66530321, 1276.32404664,
    1260.47032366, 1311.65693579, 0.0993,
    -0.2611, -2.59, 'STOP_LOSS', 6.23,
    0, '1h', '2026-03-08T18:36:22.478112'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2611,
    pnl_amount = -2.59,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0A7528A40828D369', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2021-10-16 23:00:00', '2021-10-17 10:06:31', 2651.32341534, 2635.83179489,
    2691.09326657, 2585.04032996, 0.1195,
    0.5843, 6.98, 'TRAILING_STOP', 11.11,
    1, '1h', '2026-03-08T18:36:22.478318'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5843,
    pnl_amount = 6.98,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '80C99DAC0CB1C4E9', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-10-19 14:00:00', '2021-10-20 00:58:44', 7887.63209843, 7936.15807452,
    7769.31761695, 8084.82290089, 0.095,
    0.6152, 5.84, 'TIME_EXIT', 10.98,
    1, '1h', '2026-03-08T18:36:22.483823'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6152,
    pnl_amount = 5.84,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '06304271982D3373', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-11-07 06:00:00', '2021-11-07 09:39:05', 42034.09664521, 41854.13082015,
    42664.60809489, 40983.24422908, 0.1012,
    0.4281, 4.33, 'TIME_EXIT', 3.65,
    1, '1h', '2026-03-08T18:36:22.483526'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4281,
    pnl_amount = 4.33,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A75BE1E8664F4E5F', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-11-10 05:00:00', '2021-11-10 16:31:29', 2946.68013379, 2961.83012473,
    2902.47993178, 3020.34713713, 0.0932,
    0.5141, 4.79, 'TIME_EXIT', 11.52,
    1, '1h', '2026-03-08T18:36:22.476745'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5141,
    pnl_amount = 4.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C74440A8A7305C76', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-11-10 11:00:00', '2021-11-10 14:08:33', 37159.73319299, 37057.64983035,
    36602.3371951, 38088.72652282, 0.0809,
    -0.2747, -2.22, 'STOP_LOSS', 3.14,
    0, '1h', '2026-03-08T18:36:22.482132'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2747,
    pnl_amount = -2.22,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '19A94A712D19C431', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-11-12 13:00:00', '2021-11-12 15:18:04', 4516.21343875, 4488.16879876,
    4583.95664034, 4403.30810278, 0.0968,
    0.621, 6.01, 'TAKE_PROFIT', 2.3,
    1, '1h', '2026-03-08T18:36:22.481303'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.621,
    pnl_amount = 6.01,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0C7C086248DAF43C', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-11-13 12:00:00', '2021-11-13 16:41:40', 14962.31379695, 14911.2043754,
    14737.87909, 15336.37164188, 0.0845,
    -0.3416, -2.89, 'STOP_LOSS', 4.69,
    0, '1h', '2026-03-08T18:36:22.477632'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3416,
    pnl_amount = -2.89,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EE774FFF769EFB4C', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-11-15 19:00:00', '2021-11-15 21:40:02', 2082.25334835, 2094.10604896,
    2051.01954812, 2134.30968205, 0.0803,
    0.5692, 4.57, 'TRAILING_STOP', 2.67,
    1, '1h', '2026-03-08T18:36:22.482381'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5692,
    pnl_amount = 4.57,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D0412D604CC7BE3E', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-11-16 01:00:00', '2021-11-16 03:49:13', 3161.70961245, 3142.1868611,
    3209.13525663, 3082.66687214, 0.1043,
    0.6175, 6.44, 'TAKE_PROFIT', 2.82,
    1, '1h', '2026-03-08T18:36:22.483805'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6175,
    pnl_amount = 6.44,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '65F9D9AD6B21EF6E', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-11-17 04:00:00', '2021-11-17 12:29:55', 48679.09859404, 48379.65529311,
    49409.28507295, 47462.12112919, 0.1137,
    0.6151, 6.99, 'TAKE_PROFIT', 8.5,
    1, '1h', '2026-03-08T18:36:22.483248'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6151,
    pnl_amount = 6.99,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '32E6B0AFB53CF745', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2021-11-18 05:00:00', '2021-11-18 08:33:43', 3931.91898253, 3943.05081864,
    3990.89776727, 3833.62100797, 0.0971,
    -0.2831, -2.75, 'STOP_LOSS', 3.56,
    0, '1h', '2026-03-08T18:36:22.480055'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2831,
    pnl_amount = -2.75,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C0C1CC5F89DD273B', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-11-22 16:00:00', '2021-11-23 03:28:02', 25716.8781142, 25880.17432137,
    25331.12494249, 26359.80006706, 0.0866,
    0.635, 5.5, 'TRAILING_STOP', 11.47,
    1, '1h', '2026-03-08T18:36:22.477812'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.635,
    pnl_amount = 5.5,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '37D7E7FDE2219421', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-11-24 19:00:00', '2021-11-25 04:16:52', 243.18311002, 244.18793309,
    239.53536337, 249.26268778, 0.0998,
    0.4132, 4.12, 'TIME_EXIT', 9.28,
    1, '1h', '2026-03-08T18:36:22.482036'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4132,
    pnl_amount = 4.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5F2A0569E616D42D', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-11-24 20:00:00', '2021-11-24 23:04:46', 16581.35902844, 16513.49181897,
    16830.07941386, 16166.82505273, 0.0853,
    0.4093, 3.49, 'TAKE_PROFIT', 3.08,
    1, '1h', '2026-03-08T18:36:22.479550'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4093,
    pnl_amount = 3.49,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '083CE5EB1330B1B9', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2021-11-25 22:00:00', '2021-11-26 02:33:42', 3164.18039997, 3184.01835786,
    3116.71769397, 3243.28490997, 0.0976,
    0.627, 6.12, 'TAKE_PROFIT', 4.56,
    1, '1h', '2026-03-08T18:36:22.479142'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.627,
    pnl_amount = 6.12,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3728D9D996793EAC', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2021-11-27 14:00:00', '2021-11-27 18:08:59', 3065.78362024, 3055.47238055,
    3019.79686594, 3142.42821075, 0.0892,
    -0.3363, -3.0, 'STOP_LOSS', 4.15,
    0, '1h', '2026-03-08T18:36:22.478916'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3363,
    pnl_amount = -3.0,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E55D1C37499BBFD7', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-11-27 15:00:00', '2021-11-27 19:49:38', 4461.45370174, 4488.883195,
    4394.53189622, 4572.99004429, 0.1125,
    0.6148, 6.91, 'TIME_EXIT', 4.83,
    1, '1h', '2026-03-08T18:36:22.476479'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6148,
    pnl_amount = 6.91,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B3730E92AC288045', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2021-12-02 12:00:00', '2021-12-02 22:18:52', 4519.42678192, 4535.1108751,
    4587.21818365, 4406.44111237, 0.1143,
    -0.347, -3.97, 'TIME_EXIT', 10.31,
    0, '1h', '2026-03-08T18:36:22.479339'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.347,
    pnl_amount = -3.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3DA739EA15BC089B', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2021-12-06 01:00:00', '2021-12-06 09:39:25', 458.48241432, 460.82408914,
    451.6051781, 469.94447467, 0.1136,
    0.5107, 5.8, 'TRAILING_STOP', 8.66,
    1, '1h', '2026-03-08T18:36:22.480361'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5107,
    pnl_amount = 5.8,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E0AA5DA691C21E7A', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2021-12-07 04:00:00', '2021-12-07 13:05:12', 22484.91132664, 22350.05570298,
    22822.18499654, 21922.78854347, 0.1188,
    0.5998, 7.13, 'TIME_EXIT', 9.09,
    1, '1h', '2026-03-08T18:36:22.479018'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5998,
    pnl_amount = 7.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B4012CBC2D67699A', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2021-12-11 09:00:00', '2021-12-11 12:09:56', 3193.90416713, 3174.24824868,
    3241.81272964, 3114.05656295, 0.0827,
    0.6154, 5.09, 'TIME_EXIT', 3.17,
    1, '1h', '2026-03-08T18:36:22.482027'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6154,
    pnl_amount = 5.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '620595BA08D126EC', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-12-12 13:00:00', '2021-12-13 00:44:42', 3370.85088804, 3394.38470276,
    3320.28812472, 3455.12216024, 0.1176,
    0.6982, 8.21, 'TRAILING_STOP', 11.75,
    1, '1h', '2026-03-08T18:36:22.476370'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6982,
    pnl_amount = 8.21,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8B6D4C7CFC633201', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-12-17 02:00:00', '2021-12-17 12:56:44', 2911.62144479, 2904.06086026,
    2867.94712312, 2984.41198091, 0.1162,
    -0.2597, -3.02, 'TIME_EXIT', 10.95,
    0, '1h', '2026-03-08T18:36:22.478176'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2597,
    pnl_amount = -3.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A0ACFC47C13FC2A7', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2021-12-18 23:00:00', '2021-12-19 03:05:17', 1052.25041278, 1054.95163227,
    1068.03416897, 1025.94415246, 0.0955,
    -0.2567, -2.45, 'TIME_EXIT', 4.09,
    0, '1h', '2026-03-08T18:36:22.481285'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2567,
    pnl_amount = -2.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '933B9570F47EA71D', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-12-23 06:00:00', '2021-12-23 12:02:39', 42474.40414612, 42717.46139871,
    41837.28808393, 43536.26424978, 0.0906,
    0.5722, 5.18, 'TRAILING_STOP', 6.04,
    1, '1h', '2026-03-08T18:36:22.477623'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5722,
    pnl_amount = 5.18,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1D1D43E55CFD766A', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2021-12-25 20:00:00', '2021-12-26 03:26:37', 317.16816932, 314.99348135,
    321.92569186, 309.23896508, 0.1158,
    0.6857, 7.94, 'TRAILING_STOP', 7.44,
    1, '1h', '2026-03-08T18:36:22.481417'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6857,
    pnl_amount = 7.94,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '140F46863417C8F2', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2021-12-28 06:00:00', '2021-12-28 08:15:21', 3312.55068638, 3323.34774532,
    3362.23894668, 3229.73691922, 0.1094,
    -0.3259, -3.57, 'STOP_LOSS', 2.26,
    0, '1h', '2026-03-08T18:36:22.483004'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3259,
    pnl_amount = -3.57,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '787E47D7130115D0', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2021-12-29 10:00:00', '2021-12-29 21:46:33', 3023.685908, 3006.31236461,
    3069.04119662, 2948.0937603, 0.0948,
    0.5746, 5.45, 'TIME_EXIT', 11.78,
    1, '1h', '2026-03-08T18:36:22.480288'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5746,
    pnl_amount = 5.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0324E784E55C445A', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2021-12-29 14:00:00', '2021-12-29 16:26:46', 13651.74819529, 13711.0943818,
    13446.97197236, 13993.04190017, 0.0988,
    0.4347, 4.29, 'TAKE_PROFIT', 2.45,
    1, '1h', '2026-03-08T18:36:22.476585'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4347,
    pnl_amount = 4.29,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B84A901C5E7E68E5', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2021-12-31 04:00:00', '2021-12-31 15:10:20', 4325.33942714, 4313.67377964,
    4260.45933573, 4433.47291281, 0.1155,
    -0.2697, -3.12, 'STOP_LOSS', 11.17,
    0, '1h', '2026-03-08T18:36:22.483239'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2697,
    pnl_amount = -3.12,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '056D2800E6871038', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-01-02 12:00:00', '2022-01-02 14:46:06', 567.0768007, 565.26891863,
    558.57064869, 581.25372071, 0.119,
    -0.3188, -3.79, 'TIME_EXIT', 2.77,
    0, '1h', '2026-03-08T18:36:22.479203'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3188,
    pnl_amount = -3.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7A2F631CF97E61C3', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-01-02 19:00:00', '2022-01-02 23:11:36', 2253.25035916, 2263.63585207,
    2219.45160377, 2309.58161814, 0.0944,
    0.4609, 4.35, 'TAKE_PROFIT', 4.19,
    1, '1h', '2026-03-08T18:36:22.480026'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4609,
    pnl_amount = 4.35,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F7F69EB6C30190F', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-01-02 21:00:00', '2022-01-03 01:07:44', 1348.53986743, 1357.6545759,
    1328.31176942, 1382.25336412, 0.0999,
    0.6759, 6.75, 'TIME_EXIT', 4.13,
    1, '1h', '2026-03-08T18:36:22.477569'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6759,
    pnl_amount = 6.75,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F1DF54F448A6613E', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2022-01-02 21:00:00', '2022-01-03 00:48:11', 3759.74528639, 3780.19085428,
    3703.34910709, 3853.73891855, 0.0946,
    0.5438, 5.15, 'TAKE_PROFIT', 3.8,
    1, '1h', '2026-03-08T18:36:22.478990'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5438,
    pnl_amount = 5.15,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5D8804434C200726', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-01-07 17:00:00', '2022-01-08 00:22:48', 17594.78253134, 17698.59687419,
    17330.86079337, 18034.65209463, 0.108,
    0.59, 6.37, 'TRAILING_STOP', 7.38,
    1, '1h', '2026-03-08T18:36:22.480587'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.59,
    pnl_amount = 6.37,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5DD698CB457618FB', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-01-11 18:00:00', '2022-01-11 21:31:27', 910.08125055, 904.71573981,
    923.73246931, 887.32921929, 0.0894,
    0.5896, 5.27, 'TAKE_PROFIT', 3.52,
    1, '1h', '2026-03-08T18:36:22.480614'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5896,
    pnl_amount = 5.27,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0F5BF803AC46921B', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-01-12 05:00:00', '2022-01-12 14:42:43', 3728.28935378, 3710.69880795,
    3784.21369409, 3635.08211994, 0.0843,
    0.4718, 3.98, 'TAKE_PROFIT', 9.71,
    1, '1h', '2026-03-08T18:36:22.481239'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4718,
    pnl_amount = 3.98,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ACCC4B0B8BCEE02C', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-01-13 09:00:00', '2022-01-13 12:45:57', 4678.76605045, 4699.8346769,
    4608.58455969, 4795.73520171, 0.1097,
    0.4503, 4.94, 'TIME_EXIT', 3.77,
    1, '1h', '2026-03-08T18:36:22.477653'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4503,
    pnl_amount = 4.94,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1771590C6AA836D4', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2022-01-16 22:00:00', '2022-01-17 03:37:54', 495.34055209, 497.80056742,
    487.91044381, 507.72406589, 0.0887,
    0.4966, 4.4, 'TRAILING_STOP', 5.63,
    1, '1h', '2026-03-08T18:36:22.482792'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4966,
    pnl_amount = 4.4,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F1644A5523F9D7AF', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-01-24 12:00:00', '2022-01-24 23:41:43', 1340.9062086, 1335.99261306,
    1361.01980173, 1307.38355339, 0.1124,
    0.3664, 4.12, 'TAKE_PROFIT', 11.7,
    1, '1h', '2026-03-08T18:36:22.483844'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3664,
    pnl_amount = 4.12,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '85589CA835022403', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2022-01-24 23:00:00', '2022-01-25 03:32:25', 1291.12855955, 1286.28806517,
    1310.49548794, 1258.85034556, 0.1108,
    0.3749, 4.15, 'TRAILING_STOP', 4.54,
    1, '1h', '2026-03-08T18:36:22.476929'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3749,
    pnl_amount = 4.15,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BA666D78236F1814', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2022-01-27 06:00:00', '2022-01-27 08:48:24', 2324.14962023, 2334.67186053,
    2289.28737593, 2382.25336074, 0.0973,
    0.4527, 4.4, 'TRAILING_STOP', 2.81,
    1, '1h', '2026-03-08T18:36:22.482008'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4527,
    pnl_amount = 4.4,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D06806A7E44EBD35', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2022-01-27 08:00:00', '2022-01-27 16:50:50', 1931.86708542, 1922.15394172,
    1960.8450917, 1883.57040828, 0.0959,
    0.5028, 4.82, 'TIME_EXIT', 8.85,
    1, '1h', '2026-03-08T18:36:22.482279'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5028,
    pnl_amount = 4.82,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C1797B0DF7BA1AD', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-01-27 17:00:00', '2022-01-27 22:40:38', 3032.63525259, 3043.92853549,
    2987.14572381, 3108.45113391, 0.1078,
    0.3724, 4.02, 'TIME_EXIT', 5.68,
    1, '1h', '2026-03-08T18:36:22.482243'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3724,
    pnl_amount = 4.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E3B80BBA443F5B9C', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-01-28 23:00:00', '2022-01-29 03:18:11', 4581.92587124, 4552.47771549,
    4650.65475931, 4467.37772446, 0.0829,
    0.6427, 5.33, 'TAKE_PROFIT', 4.3,
    1, '1h', '2026-03-08T18:36:22.480452'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6427,
    pnl_amount = 5.33,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7FD61367A581D2A5', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-02-02 08:00:00', '2022-02-02 15:04:57', 1337.30347716, 1330.32516674,
    1357.36302932, 1303.87089024, 0.0963,
    0.5218, 5.03, 'TRAILING_STOP', 7.08,
    1, '1h', '2026-03-08T18:36:22.480770'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5218,
    pnl_amount = 5.03,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FF44BB48C1849E61', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2022-02-08 13:00:00', '2022-02-09 00:46:10', 4264.47205471, 4281.64426297,
    4200.50497389, 4371.08385608, 0.0938,
    0.4027, 3.78, 'TAKE_PROFIT', 11.77,
    1, '1h', '2026-03-08T18:36:22.482399'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4027,
    pnl_amount = 3.78,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DB6525BC48379DD8', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-02-12 04:00:00', '2022-02-12 09:58:10', 26610.60581463, 26730.06201587,
    26211.44672741, 27275.87095999, 0.0987,
    0.4489, 4.43, 'TIME_EXIT', 5.97,
    1, '1h', '2026-03-08T18:36:22.476984'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4489,
    pnl_amount = 4.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '66BED593AD2D61D5', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2022-02-12 12:00:00', '2022-02-12 20:16:15', 4894.70052611, 4925.50578551,
    4821.28001822, 5017.06803926, 0.1124,
    0.6294, 7.08, 'TRAILING_STOP', 8.27,
    1, '1h', '2026-03-08T18:36:22.479258'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6294,
    pnl_amount = 7.08,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '956350985091407B', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-02-13 00:00:00', '2022-02-13 10:17:41', 324.73049203, 323.22080929,
    329.60144941, 316.61222973, 0.1039,
    0.4649, 4.83, 'TRAILING_STOP', 10.29,
    1, '1h', '2026-03-08T18:36:22.481389'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4649,
    pnl_amount = 4.83,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7A9F2602FE3E42EC', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-02-15 20:00:00', '2022-02-16 06:06:15', 4908.73796962, 4893.96307276,
    4835.10690008, 5031.45641886, 0.0887,
    -0.301, -2.67, 'STOP_LOSS', 10.1,
    0, '1h', '2026-03-08T18:36:22.481720'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.301,
    pnl_amount = -2.67,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C5EEA11FE1FC4A72', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-02-18 16:00:00', '2022-02-19 03:46:27', 3942.56794675, 3953.3400924,
    4001.70646596, 3844.00374808, 0.0828,
    -0.2732, -2.26, 'STOP_LOSS', 11.77,
    0, '1h', '2026-03-08T18:36:22.477293'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2732,
    pnl_amount = -2.26,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A30C45DB87E4398E', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2022-02-22 05:00:00', '2022-02-22 14:47:41', 1620.87633596, 1614.96058708,
    1645.189481, 1580.35442756, 0.0818,
    0.365, 2.98, 'TAKE_PROFIT', 9.79,
    1, '1h', '2026-03-08T18:36:22.483563'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.365,
    pnl_amount = 2.98,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '76BA808C0C844CC6', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2022-02-22 20:00:00', '2022-02-23 02:08:05', 2885.92232885, 2903.60922905,
    2842.63349392, 2958.07038707, 0.0903,
    0.6129, 5.53, 'TAKE_PROFIT', 6.13,
    1, '1h', '2026-03-08T18:36:22.480525'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6129,
    pnl_amount = 5.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D66A6D559F473CC5', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2022-02-26 14:00:00', '2022-02-26 16:09:28', 2265.80904606, 2255.37426552,
    2299.79618175, 2209.16381991, 0.0912,
    0.4605, 4.2, 'TAKE_PROFIT', 2.16,
    1, '1h', '2026-03-08T18:36:22.477058'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4605,
    pnl_amount = 4.2,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '69953BC2AD272640', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-03-08 12:00:00', '2022-03-08 18:22:35', 1653.62176129, 1645.32543971,
    1678.42608771, 1612.28121726, 0.1032,
    0.5017, 5.18, 'TAKE_PROFIT', 6.38,
    1, '1h', '2026-03-08T18:36:22.479789'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5017,
    pnl_amount = 5.18,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2BEDBE65EEB9BC2D', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2022-03-10 06:00:00', '2022-03-10 12:47:11', 4902.03271752, 4935.93412702,
    4828.50222676, 5024.58353546, 0.0951,
    0.6916, 6.58, 'TAKE_PROFIT', 6.79,
    1, '1h', '2026-03-08T18:36:22.480186'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6916,
    pnl_amount = 6.58,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C1A25DC1595540DB', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-03-10 11:00:00', '2022-03-10 13:47:28', 3412.48733158, 3400.48525499,
    3463.67464155, 3327.17514829, 0.0877,
    0.3517, 3.08, 'TRAILING_STOP', 2.79,
    1, '1h', '2026-03-08T18:36:22.481138'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3517,
    pnl_amount = 3.08,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B5F61FBBDE5ADB10', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-03-11 12:00:00', '2022-03-11 16:24:42', 3059.47951608, 3068.1211044,
    3105.37170882, 2982.99252818, 0.0923,
    -0.2825, -2.61, 'STOP_LOSS', 4.41,
    0, '1h', '2026-03-08T18:36:22.479821'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2825,
    pnl_amount = -2.61,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9AAFC27B005FEBAF', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-03-11 14:00:00', '2022-03-11 19:05:43', 3931.12887213, 3954.82737863,
    3872.16193905, 4029.40709394, 0.1199,
    0.6028, 7.23, 'TIME_EXIT', 5.1,
    1, '1h', '2026-03-08T18:36:22.480902'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6028,
    pnl_amount = 7.23,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '41222921C143172C', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-03-15 14:00:00', '2022-03-15 17:52:20', 24769.76927389, 24852.14694849,
    25141.315813, 24150.52504205, 0.1031,
    -0.3326, -3.43, 'TIME_EXIT', 3.87,
    0, '1h', '2026-03-08T18:36:22.476558'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3326,
    pnl_amount = -3.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FE06E01B150083D1', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-03-17 20:00:00', '2022-03-18 02:09:15', 2303.5994279, 2316.53896437,
    2269.04543648, 2361.1894136, 0.0903,
    0.5617, 5.07, 'TRAILING_STOP', 6.15,
    1, '1h', '2026-03-08T18:36:22.479239'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5617,
    pnl_amount = 5.07,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B3D8CE9FE2C16426', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2022-03-20 01:00:00', '2022-03-20 12:49:14', 1044.91792798, 1047.91489669,
    1060.5916969, 1018.79497978, 0.1076,
    -0.2868, -3.09, 'STOP_LOSS', 11.82,
    0, '1h', '2026-03-08T18:36:22.479405'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2868,
    pnl_amount = -3.09,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '37F9EF83DB42E22C', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-03-26 13:00:00', '2022-03-26 21:38:27', 4487.56801082, 4471.0095257,
    4554.88153098, 4375.37881055, 0.0885,
    0.369, 3.27, 'TIME_EXIT', 8.64,
    1, '1h', '2026-03-08T18:36:22.481052'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.369,
    pnl_amount = 3.27,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0962388C5D034DB6', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-04-03 13:00:00', '2022-04-03 17:08:43', 915.07913864, 911.83626558,
    928.80532572, 892.20216017, 0.0843,
    0.3544, 2.99, 'TRAILING_STOP', 4.15,
    1, '1h', '2026-03-08T18:36:22.478659'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3544,
    pnl_amount = 2.99,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6FEEDEAD3A99332F', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-04-06 14:00:00', '2022-04-07 01:49:41', 3062.86658714, 3074.32162277,
    3108.80958594, 2986.29492246, 0.0952,
    -0.374, -3.56, 'STOP_LOSS', 11.83,
    0, '1h', '2026-03-08T18:36:22.477337'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.374,
    pnl_amount = -3.56,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5FDD7A4C1E03080D', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2022-04-06 15:00:00', '2022-04-06 17:26:38', 4601.90369089, 4627.01176861,
    4532.87513553, 4716.95128316, 0.1039,
    0.5456, 5.67, 'TAKE_PROFIT', 2.44,
    1, '1h', '2026-03-08T18:36:22.481545'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5456,
    pnl_amount = 5.67,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5AB66879002FE52F', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-04-07 11:00:00', '2022-04-07 17:38:14', 28308.74693375, 28193.58064081,
    28733.37813775, 27601.0282604, 0.1082,
    0.4068, 4.4, 'TRAILING_STOP', 6.64,
    1, '1h', '2026-03-08T18:36:22.477470'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4068,
    pnl_amount = 4.4,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F2E73EEEB99A0882', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-04-07 19:00:00', '2022-04-08 02:45:49', 2690.71128017, 2704.62185364,
    2650.35061097, 2757.97906217, 0.1073,
    0.517, 5.55, 'TIME_EXIT', 7.76,
    1, '1h', '2026-03-08T18:36:22.482976'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.517,
    pnl_amount = 5.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA19844B97FA01BE', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-04-11 13:00:00', '2022-04-11 23:10:50', 1918.33853973, 1906.29259609,
    1947.11361783, 1870.38007624, 0.1058,
    0.6279, 6.64, 'TIME_EXIT', 10.18,
    1, '1h', '2026-03-08T18:36:22.478679'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6279,
    pnl_amount = 6.64,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A233551C67650843', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2022-04-12 19:00:00', '2022-04-13 06:34:31', 1233.53794951, 1229.47211312,
    1215.03488026, 1264.37639824, 0.091,
    -0.3296, -3.0, 'TIME_EXIT', 11.58,
    0, '1h', '2026-03-08T18:36:22.475825'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3296,
    pnl_amount = -3.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7B9A328BEB0F0631', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-04-13 23:00:00', '2022-04-14 04:07:08', 3808.52191464, 3790.39159629,
    3865.64974336, 3713.30886677, 0.1008,
    0.476, 4.8, 'TIME_EXIT', 5.12,
    1, '1h', '2026-03-08T18:36:22.476409'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.476,
    pnl_amount = 4.8,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1B6B2DDA070DD55D', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-04-15 00:00:00', '2022-04-15 04:59:59', 4516.16422755, 4485.58462767,
    4583.90669096, 4403.26012186, 0.1187,
    0.6771, 8.04, 'TIME_EXIT', 5.0,
    1, '1h', '2026-03-08T18:36:22.479999'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6771,
    pnl_amount = 8.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5CC0E3340482A613', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-04-15 21:00:00', '2022-04-15 23:57:56', 3269.0373748, 3251.66486116,
    3318.07293542, 3187.31144043, 0.0917,
    0.5314, 4.87, 'TAKE_PROFIT', 2.97,
    1, '1h', '2026-03-08T18:36:22.482270'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5314,
    pnl_amount = 4.87,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '97D15E967856701B', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-04-16 10:00:00', '2022-04-16 14:17:12', 1461.35367019, 1467.29282864,
    1439.43336514, 1497.88751194, 0.1077,
    0.4064, 4.38, 'TAKE_PROFIT', 4.29,
    1, '1h', '2026-03-08T18:36:22.481629'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4064,
    pnl_amount = 4.38,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '41A00C46EC3438F7', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-04-17 21:00:00', '2022-04-18 08:26:15', 31973.86938507, 31883.20746526,
    31494.2613443, 32773.2161197, 0.1138,
    -0.2836, -3.23, 'STOP_LOSS', 11.44,
    0, '1h', '2026-03-08T18:36:22.480996'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2836,
    pnl_amount = -3.23,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C4D6181974622C59', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2022-04-18 13:00:00', '2022-04-18 19:04:49', 3007.10456706, 2989.93040367,
    3052.21113557, 2931.92695288, 0.0811,
    0.5711, 4.63, 'TIME_EXIT', 6.08,
    1, '1h', '2026-03-08T18:36:22.480324'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5711,
    pnl_amount = 4.63,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FED22162187CA1B8', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-04-19 06:00:00', '2022-04-19 08:47:20', 979.37680222, 975.86033417,
    964.68615019, 1003.86122228, 0.0819,
    -0.3591, -2.94, 'STOP_LOSS', 2.79,
    0, '1h', '2026-03-08T18:36:22.479897'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3591,
    pnl_amount = -2.94,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0E40E9EFAB6AFEDD', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-04-22 13:00:00', '2022-04-22 16:31:29', 4394.46197022, 4413.15711389,
    4328.54504067, 4504.32351948, 0.1187,
    0.4254, 5.05, 'TRAILING_STOP', 3.52,
    1, '1h', '2026-03-08T18:36:22.482143'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4254,
    pnl_amount = 5.05,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '86B582FEF8C30F96', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-04-22 15:00:00', '2022-04-22 21:40:46', 33605.66785982, 33809.82104194,
    33101.58284192, 34445.80955632, 0.0862,
    0.6075, 5.24, 'TAKE_PROFIT', 6.68,
    1, '1h', '2026-03-08T18:36:22.481513'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6075,
    pnl_amount = 5.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7B0231BB7B8DE7A5', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-04-23 13:00:00', '2022-04-23 17:20:59', 2353.54914453, 2360.6559943,
    2388.85238169, 2294.71041591, 0.0823,
    -0.302, -2.49, 'TIME_EXIT', 4.35,
    0, '1h', '2026-03-08T18:36:22.483365'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.302,
    pnl_amount = -2.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F8DFA5FE4A3C2C18', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-04-23 22:00:00', '2022-04-24 08:04:28', 2032.20389847, 2039.48229242,
    2062.68695695, 1981.39880101, 0.1042,
    -0.3582, -3.73, 'STOP_LOSS', 10.07,
    0, '1h', '2026-03-08T18:36:22.478706'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3582,
    pnl_amount = -3.73,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5141B59A24DD72C5', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2022-04-27 21:00:00', '2022-04-28 08:36:34', 703.02580873, 701.0176833,
    692.4804216, 720.60145395, 0.114,
    -0.2856, -3.25, 'STOP_LOSS', 11.61,
    0, '1h', '2026-03-08T18:36:22.478354'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2856,
    pnl_amount = -3.25,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '857D2B4FF7FBCD6D', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-04-29 14:00:00', '2022-04-29 22:47:17', 6892.97490449, 6940.36998463,
    6789.58028092, 7065.2992771, 0.1035,
    0.6876, 7.12, 'TAKE_PROFIT', 8.79,
    1, '1h', '2026-03-08T18:36:22.481194'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6876,
    pnl_amount = 7.12,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A0879342FD190AD', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-05-01 01:00:00', '2022-05-01 09:36:08', 801.32689096, 798.30302005,
    789.30698759, 821.36006323, 0.1114,
    -0.3774, -4.2, 'TIME_EXIT', 8.6,
    0, '1h', '2026-03-08T18:36:22.483954'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3774,
    pnl_amount = -4.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4DC06C23B7BDE738', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-05-02 04:00:00', '2022-05-02 06:59:23', 4421.44324842, 4438.27215173,
    4487.76489715, 4310.90716721, 0.1014,
    -0.3806, -3.86, 'STOP_LOSS', 2.99,
    0, '1h', '2026-03-08T18:36:22.479776'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3806,
    pnl_amount = -3.86,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F9D7DEFE5780DE83', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-05-04 12:00:00', '2022-05-04 20:40:46', 821.76197602, 825.0460004,
    809.43554638, 842.30602542, 0.1198,
    0.3996, 4.79, 'TAKE_PROFIT', 8.68,
    1, '1h', '2026-03-08T18:36:22.482354'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3996,
    pnl_amount = 4.79,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '009C9B0F84B24DAE', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-05-09 18:00:00', '2022-05-09 22:11:36', 16215.91748742, 16164.48846025,
    15972.67872511, 16621.31542461, 0.088,
    -0.3172, -2.79, 'STOP_LOSS', 4.19,
    0, '1h', '2026-03-08T18:36:22.482985'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3172,
    pnl_amount = -2.79,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E8437904256A6662', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-05-10 04:00:00', '2022-05-10 09:50:03', 3274.30349487, 3264.72087841,
    3225.18894245, 3356.16108224, 0.0907,
    -0.2927, -2.65, 'STOP_LOSS', 5.83,
    0, '1h', '2026-03-08T18:36:22.477248'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2927,
    pnl_amount = -2.65,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9DB2D2AE8B44BAC3', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-05-13 16:00:00', '2022-05-14 00:55:58', 1324.08885809, 1330.82344999,
    1304.22752522, 1357.19107954, 0.0896,
    0.5086, 4.56, 'TAKE_PROFIT', 8.93,
    1, '1h', '2026-03-08T18:36:22.482583'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5086,
    pnl_amount = 4.56,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '68132BFCC9DED03A', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2022-05-13 21:00:00', '2022-05-14 03:43:44', 2036.88574302, 2042.58968585,
    2067.43902916, 1985.96359944, 0.1183,
    -0.28, -3.31, 'TIME_EXIT', 6.73,
    0, '1h', '2026-03-08T18:36:22.483554'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.28,
    pnl_amount = -3.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4B8749A35D8E8BBD', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-05-16 03:00:00', '2022-05-16 06:33:23', 1244.40623146, 1238.79456927,
    1263.07232494, 1213.29607568, 0.1168,
    0.451, 5.27, 'TAKE_PROFIT', 3.56,
    1, '1h', '2026-03-08T18:36:22.482457'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.451,
    pnl_amount = 5.27,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0F217A92FED40128', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-05-16 18:00:00', '2022-05-17 00:45:19', 2478.17881805, 2464.65915393,
    2515.35150032, 2416.2243476, 0.0962,
    0.5455, 5.25, 'TRAILING_STOP', 6.76,
    1, '1h', '2026-03-08T18:36:22.476391'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5455,
    pnl_amount = 5.25,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '23A704A2254903D5', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2022-05-17 22:00:00', '2022-05-18 04:53:33', 2901.48913368, 2881.52469956,
    2945.01147069, 2828.95190534, 0.09,
    0.6881, 6.19, 'TRAILING_STOP', 6.89,
    1, '1h', '2026-03-08T18:36:22.479072'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6881,
    pnl_amount = 6.19,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2BF4D0474EBB555E', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-05-18 04:00:00', '2022-05-18 06:52:29', 4568.16234545, 4546.09116043,
    4636.68478063, 4453.95828681, 0.0939,
    0.4832, 4.54, 'TIME_EXIT', 2.87,
    1, '1h', '2026-03-08T18:36:22.480378'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4832,
    pnl_amount = 4.54,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9CB2FFC709E841AC', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-05-19 00:00:00', '2022-05-19 07:29:14', 4720.59994324, 4707.28397776,
    4649.79094409, 4838.61494182, 0.1145,
    -0.2821, -3.23, 'TIME_EXIT', 7.49,
    0, '1h', '2026-03-08T18:36:22.482067'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2821,
    pnl_amount = -3.23,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '22D339E1454444F3', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2022-05-19 03:00:00', '2022-05-19 05:09:13', 1831.16644261, 1819.22391988,
    1858.63393925, 1785.38728155, 0.0932,
    0.6522, 6.08, 'TIME_EXIT', 2.15,
    1, '1h', '2026-03-08T18:36:22.475757'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6522,
    pnl_amount = 6.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '231A02A5FE9C80C5', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-05-20 16:00:00', '2022-05-21 00:56:39', 30110.39328064, 29951.46686051,
    30562.04917985, 29357.63344862, 0.0826,
    0.5278, 4.36, 'TIME_EXIT', 8.94,
    1, '1h', '2026-03-08T18:36:22.477662'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5278,
    pnl_amount = 4.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8DFA5308130D251A', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-05-22 06:00:00', '2022-05-22 08:12:11', 1106.86271573, 1112.8711877,
    1090.259775, 1134.53428363, 0.1017,
    0.5428, 5.52, 'TRAILING_STOP', 2.2,
    1, '1h', '2026-03-08T18:36:22.479585'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5428,
    pnl_amount = 5.52,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7173983C86AC234A', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-05-24 23:00:00', '2022-05-25 01:27:35', 21305.23454041, 21398.38080963,
    20985.65602231, 21837.86540392, 0.0997,
    0.4372, 4.36, 'TIME_EXIT', 2.46,
    1, '1h', '2026-03-08T18:36:22.481014'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4372,
    pnl_amount = 4.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3E7B2DF50CD51052', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-05-25 03:00:00', '2022-05-25 14:36:04', 3085.13221501, 3064.72371688,
    3131.40919824, 3008.00390964, 0.082,
    0.6615, 5.42, 'TAKE_PROFIT', 11.6,
    1, '1h', '2026-03-08T18:36:22.481903'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6615,
    pnl_amount = 5.42,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9738012F4B130A6F', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-05-25 18:00:00', '2022-05-26 01:17:29', 25116.82053797, 25009.05738479,
    25493.57284604, 24488.90002452, 0.0999,
    0.429, 4.29, 'TIME_EXIT', 7.29,
    1, '1h', '2026-03-08T18:36:22.477767'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.429,
    pnl_amount = 4.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D0355EEE6020154A', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2022-05-26 12:00:00', '2022-05-26 21:31:25', 3058.9169934, 3068.25897816,
    3104.8007483, 2982.44406857, 0.099,
    -0.3054, -3.02, 'TIME_EXIT', 9.52,
    0, '1h', '2026-03-08T18:36:22.480873'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3054,
    pnl_amount = -3.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BBB137F6E8C2363F', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2022-05-26 23:00:00', '2022-05-27 06:28:00', 4468.79931773, 4448.83633868,
    4535.8313075, 4357.07933479, 0.0933,
    0.4467, 4.17, 'TAKE_PROFIT', 7.47,
    1, '1h', '2026-03-08T18:36:22.476182'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4467,
    pnl_amount = 4.17,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F96931CE67B1C26', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2022-05-29 07:00:00', '2022-05-29 10:41:54', 2184.76370639, 2199.52438639,
    2151.9922508, 2239.38279905, 0.092,
    0.6756, 6.22, 'TAKE_PROFIT', 3.7,
    1, '1h', '2026-03-08T18:36:22.482181'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6756,
    pnl_amount = 6.22,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CC5D58658879F751', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2022-05-29 10:00:00', '2022-05-29 16:03:57', 2826.54899631, 2837.21569737,
    2868.94723125, 2755.8852714, 0.1168,
    -0.3774, -4.41, 'STOP_LOSS', 6.07,
    0, '1h', '2026-03-08T18:36:22.481980'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3774,
    pnl_amount = -4.41,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AD5CFC13CDE14996', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-05-30 03:00:00', '2022-05-30 05:19:55', 1358.03823189, 1354.48354658,
    1337.66765841, 1391.98918769, 0.0817,
    -0.2618, -2.14, 'STOP_LOSS', 2.33,
    0, '1h', '2026-03-08T18:36:22.477868'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2618,
    pnl_amount = -2.14,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F0876596225170E', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2022-05-31 13:00:00', '2022-05-31 18:42:53', 2238.40048213, 2229.48294039,
    2271.97648936, 2182.44047008, 0.1135,
    0.3984, 4.52, 'TAKE_PROFIT', 5.71,
    1, '1h', '2026-03-08T18:36:22.481111'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3984,
    pnl_amount = 4.52,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6D5EE90EB44BC5E5', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-06-09 09:00:00', '2022-06-09 18:36:27', 4022.47181586, 4005.93101355,
    4082.8088931, 3921.91002047, 0.1117,
    0.4112, 4.59, 'TAKE_PROFIT', 9.61,
    1, '1h', '2026-03-08T18:36:22.479811'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4112,
    pnl_amount = 4.59,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2C391B9B744AE269', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-06-10 13:00:00', '2022-06-10 16:43:22', 4385.72290498, 4400.78018246,
    4451.50874855, 4276.07983235, 0.0898,
    -0.3433, -3.08, 'TIME_EXIT', 3.72,
    0, '1h', '2026-03-08T18:36:22.484093'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3433,
    pnl_amount = -3.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5DFC21019BD02884', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-06-12 21:00:00', '2022-06-13 06:02:23', 4506.54007437, 4492.84389464,
    4438.94197325, 4619.20357623, 0.1124,
    -0.3039, -3.42, 'STOP_LOSS', 9.04,
    0, '1h', '2026-03-08T18:36:22.481823'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3039,
    pnl_amount = -3.42,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '03578308C989356B', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-06-13 03:00:00', '2022-06-13 09:01:12', 198.16506432, 197.4347563,
    201.13754028, 193.21093771, 0.1194,
    0.3685, 4.4, 'TAKE_PROFIT', 6.02,
    1, '1h', '2026-03-08T18:36:22.483212'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3685,
    pnl_amount = 4.4,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5D2526695C4CE2BA', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-06-13 13:00:00', '2022-06-13 18:44:19', 2891.90870236, 2903.77364598,
    2848.53007183, 2964.20641992, 0.1135,
    0.4103, 4.66, 'TAKE_PROFIT', 5.74,
    1, '1h', '2026-03-08T18:36:22.483022'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4103,
    pnl_amount = 4.66,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B7C3A4FBEA75E9B6', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-06-15 18:00:00', '2022-06-15 22:09:23', 4620.4474896, 4605.73081505,
    4551.14077725, 4735.95867684, 0.1103,
    -0.3185, -3.51, 'STOP_LOSS', 4.16,
    0, '1h', '2026-03-08T18:36:22.478735'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3185,
    pnl_amount = -3.51,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B19D64CF7A1C5139', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-06-18 06:00:00', '2022-06-18 11:36:53', 2629.68892123, 2642.7847429,
    2590.24358741, 2695.43114426, 0.1138,
    0.498, 5.67, 'TAKE_PROFIT', 5.61,
    1, '1h', '2026-03-08T18:36:22.483257'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.498,
    pnl_amount = 5.67,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A76C19E03C169603', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-06-20 18:00:00', '2022-06-21 04:53:13', 2256.31775014, 2250.10530193,
    2222.47298389, 2312.72569389, 0.1056,
    -0.2753, -2.91, 'TIME_EXIT', 10.89,
    0, '1h', '2026-03-08T18:36:22.484072'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2753,
    pnl_amount = -2.91,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '105AF30FD84F5171', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-06-21 03:00:00', '2022-06-21 12:13:40', 3695.06114531, 3719.5633701,
    3639.63522813, 3787.43767394, 0.089,
    0.6631, 5.9, 'TRAILING_STOP', 9.23,
    1, '1h', '2026-03-08T18:36:22.477031'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6631,
    pnl_amount = 5.9,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B8B4C0609C68DC3C', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-06-22 16:00:00', '2022-06-22 21:57:08', 805.62931995, 801.53094493,
    817.71375975, 785.48858695, 0.0977,
    0.5087, 4.97, 'TIME_EXIT', 5.95,
    1, '1h', '2026-03-08T18:36:22.476266'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5087,
    pnl_amount = 4.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6B250DDFA4C5C955', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-06-23 08:00:00', '2022-06-23 19:00:07', 2769.10754738, 2755.03111845,
    2810.64416059, 2699.8798587, 0.0957,
    0.5083, 4.87, 'TAKE_PROFIT', 11.0,
    1, '1h', '2026-03-08T18:36:22.477355'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5083,
    pnl_amount = 4.87,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B501E591398A1FBC', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-06-23 17:00:00', '2022-06-23 21:37:23', 4275.89866336, 4263.44249114,
    4211.76018341, 4382.79612995, 0.1015,
    -0.2913, -2.96, 'STOP_LOSS', 4.62,
    0, '1h', '2026-03-08T18:36:22.482940'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2913,
    pnl_amount = -2.96,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7ECAD34FDB6DF2BC', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-06-24 09:00:00', '2022-06-24 14:17:29', 2563.05049728, 2576.28218018,
    2524.60473982, 2627.12675971, 0.0902,
    0.5162, 4.66, 'TIME_EXIT', 5.29,
    1, '1h', '2026-03-08T18:36:22.477488'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5162,
    pnl_amount = 4.66,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2AC46F0982A9F4A3', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2022-06-28 02:00:00', '2022-06-28 10:41:31', 114.38055718, 113.61321555,
    116.09626554, 111.52104325, 0.1046,
    0.6709, 7.02, 'TIME_EXIT', 8.69,
    1, '1h', '2026-03-08T18:36:22.477394'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6709,
    pnl_amount = 7.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '731D6AF0D8FCD40D', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-06-28 22:00:00', '2022-06-29 03:44:20', 2285.66121621, 2277.35408095,
    2251.37629796, 2342.80274661, 0.0919,
    -0.3634, -3.34, 'STOP_LOSS', 5.74,
    0, '1h', '2026-03-08T18:36:22.477186'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3634,
    pnl_amount = -3.34,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '044D01C2BA3D9E55', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-06-29 02:00:00', '2022-06-29 12:25:08', 2122.33007272, 2135.8063498,
    2090.49512163, 2175.38832454, 0.1067,
    0.635, 6.77, 'TIME_EXIT', 10.42,
    1, '1h', '2026-03-08T18:36:22.475895'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.635,
    pnl_amount = 6.77,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D0AE04FDF3A27CF8', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-07-03 05:00:00', '2022-07-03 12:14:33', 2397.9974829, 2390.1612908,
    2362.02752066, 2457.94741997, 0.0898,
    -0.3268, -2.93, 'STOP_LOSS', 7.24,
    0, '1h', '2026-03-08T18:36:22.483474'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3268,
    pnl_amount = -2.93,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CD85E4045633AA9C', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-07-03 11:00:00', '2022-07-03 19:56:45', 3461.71827028, 3474.01752774,
    3513.64404433, 3375.17531352, 0.1162,
    -0.3553, -4.13, 'TIME_EXIT', 8.95,
    0, '1h', '2026-03-08T18:36:22.483135'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3553,
    pnl_amount = -4.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F3AEAFC0D17688F9', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2022-07-03 22:00:00', '2022-07-04 01:05:30', 493.6600717, 495.50575182,
    486.25517063, 506.0015735, 0.0998,
    0.3739, 3.73, 'TRAILING_STOP', 3.09,
    1, '1h', '2026-03-08T18:36:22.478670'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3739,
    pnl_amount = 3.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EDEB880762FCD57E', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-07-06 13:00:00', '2022-07-06 18:05:35', 2901.60793958, 2912.59899136,
    2858.08382048, 2974.14813806, 0.1126,
    0.3788, 4.26, 'TIME_EXIT', 5.09,
    1, '1h', '2026-03-08T18:36:22.478014'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3788,
    pnl_amount = 4.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '140D796A1EB68FA4', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-07-07 07:00:00', '2022-07-07 17:56:34', 24001.73129644, 24166.7468971,
    23641.70532699, 24601.77457885, 0.0832,
    0.6875, 5.72, 'TIME_EXIT', 10.94,
    1, '1h', '2026-03-08T18:36:22.480967'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6875,
    pnl_amount = 5.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BC2FD94EFFD85DAC', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-07-08 07:00:00', '2022-07-08 09:56:11', 30.43357607, 30.53993374,
    30.89007971, 29.67273667, 0.1164,
    -0.3495, -4.07, 'TIME_EXIT', 2.94,
    0, '1h', '2026-03-08T18:36:22.481940'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3495,
    pnl_amount = -4.07,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '39E849AF58A26B81', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2022-07-10 19:00:00', '2022-07-10 23:55:06', 2919.13327552, 2900.54549405,
    2962.92027465, 2846.15494363, 0.0931,
    0.6368, 5.93, 'TRAILING_STOP', 4.92,
    1, '1h', '2026-03-08T18:36:22.476629'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6368,
    pnl_amount = 5.93,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '588FD6EE94841468', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-07-12 20:00:00', '2022-07-13 05:16:05', 4351.19274616, 4371.95590295,
    4285.92485497, 4459.97256482, 0.1133,
    0.4772, 5.4, 'TIME_EXIT', 9.27,
    1, '1h', '2026-03-08T18:36:22.482335'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4772,
    pnl_amount = 5.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '20169E0F7D1196CE', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-07-13 16:00:00', '2022-07-14 03:27:27', 1643.2724039, 1632.67230383,
    1667.92148996, 1602.19059381, 0.1185,
    0.6451, 7.64, 'TRAILING_STOP', 11.46,
    1, '1h', '2026-03-08T18:36:22.481230'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6451,
    pnl_amount = 7.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1A9DAEFD9B467066', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-07-15 22:00:00', '2022-07-16 00:58:44', 41504.15979381, 41270.37355608,
    42126.72219072, 40466.55579897, 0.0986,
    0.5633, 5.55, 'TIME_EXIT', 2.98,
    1, '1h', '2026-03-08T18:36:22.479461'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5633,
    pnl_amount = 5.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA53D090FE12FC3C', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-07-16 18:00:00', '2022-07-17 03:34:31', 23163.67801894, 23241.31453924,
    23511.13318923, 22584.58606847, 0.0926,
    -0.3352, -3.1, 'TIME_EXIT', 9.58,
    0, '1h', '2026-03-08T18:36:22.476145'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3352,
    pnl_amount = -3.1,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D1D15EAB4A001C34', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-07-18 23:00:00', '2022-07-19 02:17:07', 1545.64915012, 1553.36318036,
    1522.46441286, 1584.29037887, 0.0888,
    0.4991, 4.43, 'TRAILING_STOP', 3.29,
    1, '1h', '2026-03-08T18:36:22.483179'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4991,
    pnl_amount = 4.43,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B7EA0E7E7343ED44', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-07-19 03:00:00', '2022-07-19 12:34:43', 7768.06568944, 7814.60690396,
    7651.5447041, 7962.26733167, 0.1043,
    0.5991, 6.25, 'TRAILING_STOP', 9.58,
    1, '1h', '2026-03-08T18:36:22.483617'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5991,
    pnl_amount = 6.25,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '95B3BD777229A137', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-07-19 12:00:00', '2022-07-19 21:59:43', 2862.74412108, 2843.05468401,
    2905.6852829, 2791.17551805, 0.0916,
    0.6878, 6.3, 'TIME_EXIT', 10.0,
    1, '1h', '2026-03-08T18:36:22.476030'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6878,
    pnl_amount = 6.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F57565DEEB447A18', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-07-20 12:00:00', '2022-07-20 19:52:34', 1489.91994934, 1495.60236856,
    1467.5711501, 1527.16794807, 0.0977,
    0.3814, 3.72, 'TIME_EXIT', 7.88,
    1, '1h', '2026-03-08T18:36:22.480148'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3814,
    pnl_amount = 3.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DC51086C8D904249', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-07-21 20:00:00', '2022-07-22 07:44:26', 1020.08502467, 1013.27493533,
    1035.38630004, 994.58289905, 0.101,
    0.6676, 6.74, 'TIME_EXIT', 11.74,
    1, '1h', '2026-03-08T18:36:22.482685'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6676,
    pnl_amount = 6.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0196E6826086C950', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-07-23 10:00:00', '2022-07-23 18:21:43', 3884.69597862, 3900.35548375,
    3826.42553894, 3981.81337809, 0.1059,
    0.4031, 4.27, 'TRAILING_STOP', 8.36,
    1, '1h', '2026-03-08T18:36:22.482693'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4031,
    pnl_amount = 4.27,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2A7E28FDB85297D0', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2022-08-03 08:00:00', '2022-08-03 18:40:18', 851.37270037, 855.76883257,
    838.60210986, 872.65701787, 0.0979,
    0.5164, 5.06, 'TRAILING_STOP', 10.67,
    1, '1h', '2026-03-08T18:36:22.478085'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5164,
    pnl_amount = 5.06,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4A9D61FD53C5C56F', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-08-05 04:00:00', '2022-08-05 15:24:51', 2053.8825314, 2043.34102358,
    2084.69076937, 2002.53546811, 0.1104,
    0.5132, 5.67, 'TIME_EXIT', 11.41,
    1, '1h', '2026-03-08T18:36:22.477785'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5132,
    pnl_amount = 5.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '76C733F681701055', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-08-05 13:00:00', '2022-08-05 19:21:33', 3768.52897117, 3788.53218153,
    3712.0010366, 3862.74219545, 0.0992,
    0.5308, 5.26, 'TAKE_PROFIT', 6.36,
    1, '1h', '2026-03-08T18:36:22.477711'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5308,
    pnl_amount = 5.26,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9D16BA378CA511D0', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-08-07 11:00:00', '2022-08-07 15:20:20', 4000.68406396, 4024.93098521,
    3940.673803, 4100.70116556, 0.0849,
    0.6061, 5.15, 'TRAILING_STOP', 4.34,
    1, '1h', '2026-03-08T18:36:22.480461'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6061,
    pnl_amount = 5.15,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '06D59EF4A18D098B', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-08-08 02:00:00', '2022-08-08 13:38:20', 866.78320331, 861.35873829,
    879.78495136, 845.11362322, 0.0851,
    0.6258, 5.32, 'TAKE_PROFIT', 11.64,
    1, '1h', '2026-03-08T18:36:22.482564'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6258,
    pnl_amount = 5.32,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD742EE8880E6AEA', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2022-08-08 13:00:00', '2022-08-08 23:24:35', 3991.13113054, 4017.97797151,
    3931.26416358, 4090.9094088, 0.1042,
    0.6727, 7.01, 'TAKE_PROFIT', 10.41,
    1, '1h', '2026-03-08T18:36:22.479693'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6727,
    pnl_amount = 7.01,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '155F599E1081523B', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-08-11 20:00:00', '2022-08-12 07:48:52', 4127.3383954, 4139.16478628,
    4189.24847133, 4024.15493551, 0.1093,
    -0.2865, -3.13, 'STOP_LOSS', 11.81,
    0, '1h', '2026-03-08T18:36:22.483517'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2865,
    pnl_amount = -3.13,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A0D183D6A28B0BED', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-08-15 05:00:00', '2022-08-15 14:06:11', 2274.62489566, 2289.6473553,
    2240.50552223, 2331.49051806, 0.1199,
    0.6604, 7.92, 'TIME_EXIT', 9.1,
    1, '1h', '2026-03-08T18:36:22.477040'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6604,
    pnl_amount = 7.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '424B904C747ED3D5', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-08-17 11:00:00', '2022-08-17 14:09:14', 530.42383905, 532.4211636,
    522.46748147, 543.68443503, 0.1104,
    0.3766, 4.16, 'TAKE_PROFIT', 3.15,
    1, '1h', '2026-03-08T18:36:22.481961'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3766,
    pnl_amount = 4.16,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EEF3368880638873', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2022-08-17 23:00:00', '2022-08-18 01:06:48', 61.62590407, 61.86100157,
    60.70151551, 63.16655167, 0.0881,
    0.3815, 3.36, 'TIME_EXIT', 2.11,
    1, '1h', '2026-03-08T18:36:22.480216'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3815,
    pnl_amount = 3.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8D75CCDEFBFBA590', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-08-20 19:00:00', '2022-08-21 00:11:38', 3681.57214739, 3695.66336095,
    3626.34856518, 3773.61145108, 0.1041,
    0.3827, 3.98, 'TRAILING_STOP', 5.19,
    1, '1h', '2026-03-08T18:36:22.476440'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3827,
    pnl_amount = 3.98,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0A77B0EDCBB2BD31', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-08-22 08:00:00', '2022-08-22 17:29:44', 2542.55044455, 2525.24979424,
    2580.68870122, 2478.98668344, 0.0879,
    0.6804, 5.98, 'TIME_EXIT', 9.5,
    1, '1h', '2026-03-08T18:36:22.481408'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6804,
    pnl_amount = 5.98,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C3C019B3BF8910F4', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-08-22 15:00:00', '2022-08-23 01:45:12', 4906.33085267, 4939.91502584,
    4832.73588988, 5028.98912398, 0.0832,
    0.6845, 5.69, 'TRAILING_STOP', 10.75,
    1, '1h', '2026-03-08T18:36:22.481075'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6845,
    pnl_amount = 5.69,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9B025C4114B6EE01', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2022-08-23 13:00:00', '2022-08-23 18:21:09', 768.20221088, 765.04941232,
    779.72524404, 748.99715561, 0.1003,
    0.4104, 4.12, 'TIME_EXIT', 5.35,
    1, '1h', '2026-03-08T18:36:22.480157'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4104,
    pnl_amount = 4.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '123733688A94AA6C', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-08-25 21:00:00', '2022-08-26 04:32:11', 3440.71049169, 3428.41318922,
    3389.09983431, 3526.72825398, 0.1144,
    -0.3574, -4.09, 'TIME_EXIT', 7.54,
    0, '1h', '2026-03-08T18:36:22.478897'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3574,
    pnl_amount = -4.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96E4A59F858E106C', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-08-26 15:00:00', '2022-08-26 22:48:12', 827.81639661, 824.954843,
    815.39915066, 848.51180652, 0.0881,
    -0.3457, -3.04, 'TIME_EXIT', 7.8,
    0, '1h', '2026-03-08T18:36:22.476706'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3457,
    pnl_amount = -3.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '836D9D68E60D4374', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2022-08-27 18:00:00', '2022-08-28 02:39:33', 3568.1478707, 3553.16370062,
    3621.67008876, 3478.94417393, 0.1007,
    0.4199, 4.23, 'TRAILING_STOP', 8.66,
    1, '1h', '2026-03-08T18:36:22.482468'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4199,
    pnl_amount = 4.23,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DE1BAE4E878B43A6', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2022-09-01 17:00:00', '2022-09-01 19:29:50', 3018.56515169, 3028.18260701,
    3063.84362897, 2943.1010229, 0.0971,
    -0.3186, -3.09, 'TIME_EXIT', 2.5,
    0, '1h', '2026-03-08T18:36:22.477329'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3186,
    pnl_amount = -3.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5BBFF417DEC780DB', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-09-01 17:00:00', '2022-09-02 02:13:21', 4809.70707278, 4781.58678136,
    4881.85267887, 4689.46439596, 0.1133,
    0.5847, 6.62, 'TAKE_PROFIT', 9.22,
    1, '1h', '2026-03-08T18:36:22.479098'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5847,
    pnl_amount = 6.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '73F94FD4676471C2', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-09-06 18:00:00', '2022-09-07 02:47:29', 1059.23744811, 1053.04667721,
    1075.12600984, 1032.75651191, 0.1089,
    0.5845, 6.37, 'TAKE_PROFIT', 8.79,
    1, '1h', '2026-03-08T18:36:22.480497'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5845,
    pnl_amount = 6.37,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '48FC4D43282B46E8', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2022-09-06 20:00:00', '2022-09-06 23:27:13', 1159.8939851, 1156.01688961,
    1142.49557533, 1188.89133473, 0.1171,
    -0.3343, -3.92, 'STOP_LOSS', 3.45,
    0, '1h', '2026-03-08T18:36:22.477076'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3343,
    pnl_amount = -3.92,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CEDB28ECD047E772', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2022-09-09 19:00:00', '2022-09-09 23:11:27', 4995.98988182, 4962.87476988,
    5070.92973004, 4871.09013477, 0.0826,
    0.6628, 5.47, 'TRAILING_STOP', 4.19,
    1, '1h', '2026-03-08T18:36:22.480128'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6628,
    pnl_amount = 5.47,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10AB1F4A376A6F25', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-09-09 19:00:00', '2022-09-09 22:45:22', 39429.6144416, 39561.85470888,
    40021.05865823, 38443.87408056, 0.0908,
    -0.3354, -3.04, 'TIME_EXIT', 3.76,
    0, '1h', '2026-03-08T18:36:22.482738'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3354,
    pnl_amount = -3.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0DC6CFBBD34ECAC3', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-09-10 15:00:00', '2022-09-10 19:18:18', 1534.60008857, 1544.44852102,
    1511.58108724, 1572.96509078, 0.0911,
    0.6418, 5.84, 'TAKE_PROFIT', 4.31,
    1, '1h', '2026-03-08T18:36:22.480569'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6418,
    pnl_amount = 5.84,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EAC831433424E847', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2022-09-14 17:00:00', '2022-09-14 19:59:00', 2714.73792528, 2705.29679195,
    2674.0168564, 2782.60637341, 0.0966,
    -0.3478, -3.36, 'STOP_LOSS', 2.98,
    0, '1h', '2026-03-08T18:36:22.476594'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3478,
    pnl_amount = -3.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F7BB019081925E9F', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2022-09-23 02:00:00', '2022-09-23 05:23:02', 2813.94552605, 2804.44922147,
    2771.73634316, 2884.29416421, 0.0985,
    -0.3375, -3.32, 'TIME_EXIT', 3.38,
    0, '1h', '2026-03-08T18:36:22.478823'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3375,
    pnl_amount = -3.32,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5573C304403BC5A7', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-09-26 05:00:00', '2022-09-26 11:35:48', 2072.12578454, 2082.3981389,
    2041.04389777, 2123.92892916, 0.1038,
    0.4957, 5.15, 'TAKE_PROFIT', 6.6,
    1, '1h', '2026-03-08T18:36:22.475963'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4957,
    pnl_amount = 5.15,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7BD3ABE183EB234E', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-09-26 18:00:00', '2022-09-27 00:03:18', 27993.70726027, 27867.77156665,
    28413.61286917, 27293.86457876, 0.0937,
    0.4499, 4.22, 'TRAILING_STOP', 6.06,
    1, '1h', '2026-03-08T18:36:22.480243'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4499,
    pnl_amount = 4.22,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D93EBF64B5487710', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-09-27 02:00:00', '2022-09-27 09:42:49', 23922.06607055, 23858.85241654,
    23563.23507949, 24520.11772231, 0.0947,
    -0.2642, -2.5, 'TIME_EXIT', 7.71,
    0, '1h', '2026-03-08T18:36:22.479377'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2642,
    pnl_amount = -2.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AD4AD1F5DCA3BC58', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-09-28 01:00:00', '2022-09-28 03:47:47', 24291.29676839, 24376.94586279,
    23926.92731686, 24898.5791876, 0.1059,
    0.3526, 3.73, 'TAKE_PROFIT', 2.8,
    1, '1h', '2026-03-08T18:36:22.478309'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3526,
    pnl_amount = 3.73,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '08EC9383523AA101', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2022-09-28 01:00:00', '2022-09-28 06:31:49', 3790.15053475, 3799.92835818,
    3847.00279277, 3695.39677138, 0.0958,
    -0.258, -2.47, 'TIME_EXIT', 5.53,
    0, '1h', '2026-03-08T18:36:22.480045'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.258,
    pnl_amount = -2.47,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '12B413E633313A80', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-10-01 07:00:00', '2022-10-01 10:14:12', 12915.37985281, 12879.27966666,
    12721.64915501, 13238.26434913, 0.1176,
    -0.2795, -3.29, 'STOP_LOSS', 3.24,
    0, '1h', '2026-03-08T18:36:22.483495'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2795,
    pnl_amount = -3.29,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7C021160CA053351', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-10-12 02:00:00', '2022-10-12 04:22:19', 1874.71457295, 1865.41037395,
    1902.83529154, 1827.84670862, 0.0846,
    0.4963, 4.2, 'TIME_EXIT', 2.37,
    1, '1h', '2026-03-08T18:36:22.483328'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4963,
    pnl_amount = 4.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C772CC2FEC2F696C', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-10-14 05:00:00', '2022-10-14 07:42:35', 2872.6919889, 2882.13545282,
    2915.78236874, 2800.87468918, 0.0893,
    -0.3287, -2.94, 'STOP_LOSS', 2.71,
    0, '1h', '2026-03-08T18:36:22.484115'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3287,
    pnl_amount = -2.94,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2B3357A1B126DD8C', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-10-15 14:00:00', '2022-10-15 20:27:18', 1845.27281408, 1854.58181917,
    1817.59372187, 1891.40463443, 0.0921,
    0.5045, 4.65, 'TAKE_PROFIT', 6.46,
    1, '1h', '2026-03-08T18:36:22.479177'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5045,
    pnl_amount = 4.65,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A56E17C514D71E3', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-10-16 22:00:00', '2022-10-17 05:52:18', 2490.05562889, 2499.69774077,
    2452.70479446, 2552.30701962, 0.0828,
    0.3872, 3.21, 'TIME_EXIT', 7.87,
    1, '1h', '2026-03-08T18:36:22.476656'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3872,
    pnl_amount = 3.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '18E7C5661514AA92', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-10-17 18:00:00', '2022-10-18 03:24:18', 31043.91408603, 30933.3994993,
    30578.25537474, 31820.01193818, 0.0945,
    -0.356, -3.36, 'STOP_LOSS', 9.41,
    0, '1h', '2026-03-08T18:36:22.476381'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.356,
    pnl_amount = -3.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7FABFE025ED23294', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2022-10-19 03:00:00', '2022-10-19 07:43:15', 366.58264377, 367.74252387,
    372.08138343, 357.41807768, 0.0958,
    -0.3164, -3.03, 'TIME_EXIT', 4.72,
    0, '1h', '2026-03-08T18:36:22.483991'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3164,
    pnl_amount = -3.03,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4DCDC525CFB947F8', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-10-22 23:00:00', '2022-10-23 10:36:05', 4327.71051838, 4302.94998088,
    4392.62617615, 4219.51775542, 0.0917,
    0.5721, 5.25, 'TAKE_PROFIT', 11.6,
    1, '1h', '2026-03-08T18:36:22.483875'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5721,
    pnl_amount = 5.25,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '071D5D4DB2D2231C', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2022-10-29 23:00:00', '2022-10-30 06:32:43', 2201.78299466, 2186.47087303,
    2234.80973958, 2146.73841979, 0.1025,
    0.6954, 7.13, 'TAKE_PROFIT', 7.55,
    1, '1h', '2026-03-08T18:36:22.479674'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6954,
    pnl_amount = 7.13,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B4528EC544CB5574', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-10-30 11:00:00', '2022-10-30 20:41:55', 680.62041962, 678.20925904,
    690.82972592, 663.60490913, 0.1198,
    0.3543, 4.24, 'TAKE_PROFIT', 9.7,
    1, '1h', '2026-03-08T18:36:22.482783'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3543,
    pnl_amount = 4.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E6044CD944EF0038', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-11-02 00:00:00', '2022-11-02 04:38:23', 3513.03386039, 3503.33174334,
    3460.33835249, 3600.8597069, 0.0981,
    -0.2762, -2.71, 'STOP_LOSS', 4.64,
    0, '1h', '2026-03-08T18:36:22.483972'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2762,
    pnl_amount = -2.71,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6148E4947391902A', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-11-07 01:00:00', '2022-11-07 08:56:40', 36917.09770633, 37119.99043536,
    36363.34124074, 37840.02514899, 0.0877,
    0.5496, 4.82, 'TIME_EXIT', 7.94,
    1, '1h', '2026-03-08T18:36:22.477266'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5496,
    pnl_amount = 4.82,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '949004F6E6BCAF95', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-11-07 22:00:00', '2022-11-08 09:07:25', 38739.88465723, 38843.92000696,
    39320.98292708, 37771.3875408, 0.0834,
    -0.2685, -2.24, 'STOP_LOSS', 11.12,
    0, '1h', '2026-03-08T18:36:22.477382'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2685,
    pnl_amount = -2.24,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E84AE03572E1621C', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2022-11-09 21:00:00', '2022-11-10 05:31:59', 4886.4828626, 4869.29154881,
    4959.78010553, 4764.32079103, 0.0897,
    0.3518, 3.16, 'TRAILING_STOP', 8.53,
    1, '1h', '2026-03-08T18:36:22.483438'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3518,
    pnl_amount = 3.16,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '82F553D10A9C06F7', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-11-10 04:00:00', '2022-11-10 08:04:47', 3422.52406212, 3409.48801085,
    3371.18620119, 3508.08716368, 0.1095,
    -0.3809, -4.17, 'STOP_LOSS', 4.08,
    0, '1h', '2026-03-08T18:36:22.478103'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3809,
    pnl_amount = -4.17,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD7D21AAC531F1F7', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-11-18 01:00:00', '2022-11-18 10:23:38', 3015.74503136, 3000.67052003,
    3060.98120683, 2940.35140557, 0.0933,
    0.4999, 4.66, 'TRAILING_STOP', 9.39,
    1, '1h', '2026-03-08T18:36:22.482592'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4999,
    pnl_amount = 4.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1869F14193EFD059', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2022-11-19 16:00:00', '2022-11-20 02:53:25', 1717.58885255, 1708.25403002,
    1743.35268534, 1674.64913124, 0.0903,
    0.5435, 4.91, 'TRAILING_STOP', 10.89,
    1, '1h', '2026-03-08T18:36:22.480470'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5435,
    pnl_amount = 4.91,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C3A105E2448336A1', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2022-11-20 12:00:00', '2022-11-20 22:31:48', 1211.56969932, 1216.92618557,
    1193.39615383, 1241.85894181, 0.1168,
    0.4421, 5.17, 'TAKE_PROFIT', 10.53,
    1, '1h', '2026-03-08T18:36:22.478521'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4421,
    pnl_amount = 5.17,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '349B23BCD6527A95', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2022-11-21 11:00:00', '2022-11-21 15:09:29', 2883.47671863, 2900.05305409,
    2840.22456785, 2955.56363659, 0.0856,
    0.5749, 4.92, 'TIME_EXIT', 4.16,
    1, '1h', '2026-03-08T18:36:22.482086'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5749,
    pnl_amount = 4.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4DB8F0452013D7FC', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-11-23 12:00:00', '2022-11-23 22:15:44', 4802.42387006, 4772.45913725,
    4874.46022811, 4682.36327331, 0.1155,
    0.624, 7.21, 'TIME_EXIT', 10.26,
    1, '1h', '2026-03-08T18:36:22.482774'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.624,
    pnl_amount = 7.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D531DE5031C46648', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-11-26 07:00:00', '2022-11-26 11:04:49', 4736.95035969, 4723.60328689,
    4665.8961043, 4855.37411868, 0.1183,
    -0.2818, -3.33, 'STOP_LOSS', 4.08,
    0, '1h', '2026-03-08T18:36:22.480234'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2818,
    pnl_amount = -3.33,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C564D887A47803DB', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2022-11-26 17:00:00', '2022-11-27 03:21:15', 4411.52080723, 4437.4221397,
    4345.34799513, 4521.80882742, 0.0949,
    0.5871, 5.57, 'TAKE_PROFIT', 10.35,
    1, '1h', '2026-03-08T18:36:22.482837'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5871,
    pnl_amount = 5.57,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A11CC89C12D844F3', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-11-28 15:00:00', '2022-11-28 21:00:14', 1557.07459323, 1550.04282996,
    1580.43071213, 1518.1477284, 0.1193,
    0.4516, 5.39, 'TIME_EXIT', 6.0,
    1, '1h', '2026-03-08T18:36:22.482911'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4516,
    pnl_amount = 5.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '88C8370F20CC85CC', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-11-30 20:00:00', '2022-11-30 23:45:15', 40135.89587821, 39985.6450379,
    40737.93431638, 39132.49848125, 0.1117,
    0.3744, 4.18, 'TIME_EXIT', 3.75,
    1, '1h', '2026-03-08T18:36:22.477680'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3744,
    pnl_amount = 4.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1FCE9EAF71822C0C', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2022-12-01 03:00:00', '2022-12-01 11:32:20', 3871.36208275, 3886.11894886,
    3929.43251399, 3774.57803068, 0.0861,
    -0.3812, -3.28, 'STOP_LOSS', 8.54,
    0, '1h', '2026-03-08T18:36:22.477213'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3812,
    pnl_amount = -3.28,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B3A254753F33926A', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-12-05 00:00:00', '2022-12-05 06:47:28', 19655.04173338, 19738.44884083,
    19360.21610738, 20146.41777672, 0.1109,
    0.4244, 4.71, 'TIME_EXIT', 6.79,
    1, '1h', '2026-03-08T18:36:22.483230'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4244,
    pnl_amount = 4.71,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '549C09E6448A23CE', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2022-12-08 15:00:00', '2022-12-09 00:44:18', 1776.5814131, 1771.10979322,
    1749.93269191, 1820.99594843, 0.1077,
    -0.308, -3.32, 'STOP_LOSS', 9.74,
    0, '1h', '2026-03-08T18:36:22.478059'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.308,
    pnl_amount = -3.32,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D7058819D16312A5', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2022-12-12 11:00:00', '2022-12-12 19:10:36', 21075.33142566, 20969.71336414,
    21391.46139704, 20548.44814002, 0.0946,
    0.5011, 4.74, 'TAKE_PROFIT', 8.18,
    1, '1h', '2026-03-08T18:36:22.480008'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5011,
    pnl_amount = 4.74,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F883E5B416172980', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2022-12-13 17:00:00', '2022-12-13 21:03:11', 1478.81019818, 1473.71401393,
    1456.6280452, 1515.78045313, 0.0964,
    -0.3446, -3.32, 'STOP_LOSS', 4.05,
    0, '1h', '2026-03-08T18:36:22.480623'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3446,
    pnl_amount = -3.32,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A1FB01C0F8B8DBC3', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-12-13 21:00:00', '2022-12-14 07:04:08', 19239.54395204, 19348.34619048,
    18950.95079276, 19720.53255084, 0.1117,
    0.5655, 6.32, 'TRAILING_STOP', 10.07,
    1, '1h', '2026-03-08T18:36:22.477578'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5655,
    pnl_amount = 6.32,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BC8C1FEB21C86B15', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-12-13 23:00:00', '2022-12-14 10:51:07', 765.06131425, 769.006754,
    753.58539454, 784.18784711, 0.1147,
    0.5157, 5.92, 'TIME_EXIT', 11.85,
    1, '1h', '2026-03-08T18:36:22.476864'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5157,
    pnl_amount = 5.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC866DC6F24F2C69', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2022-12-14 13:00:00', '2022-12-14 18:33:53', 2032.43746965, 2025.1714589,
    2001.95090761, 2083.24840639, 0.0894,
    -0.3575, -3.19, 'STOP_LOSS', 5.56,
    0, '1h', '2026-03-08T18:36:22.476488'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3575,
    pnl_amount = -3.19,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4CCEAC33F7F32CF9', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2022-12-17 10:00:00', '2022-12-17 12:16:11', 1020.78256436, 1014.93533116,
    1036.09430282, 995.26300025, 0.0973,
    0.5728, 5.58, 'TAKE_PROFIT', 2.27,
    1, '1h', '2026-03-08T18:36:22.478697'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5728,
    pnl_amount = 5.58,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7E951BB8EDF3B2B3', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-12-20 23:00:00', '2022-12-21 09:14:53', 4151.30193157, 4171.21972212,
    4089.0324026, 4255.08447986, 0.0995,
    0.4798, 4.78, 'TRAILING_STOP', 10.25,
    1, '1h', '2026-03-08T18:36:22.478050'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4798,
    pnl_amount = 4.78,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A335171FF58C599', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2022-12-21 16:00:00', '2022-12-21 19:19:59', 2587.38715198, 2596.6985817,
    2548.5763447, 2652.07183078, 0.1003,
    0.3599, 3.61, 'TIME_EXIT', 3.33,
    1, '1h', '2026-03-08T18:36:22.480677'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3599,
    pnl_amount = 3.61,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '933F0FD4ECDD11D5', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2022-12-22 18:00:00', '2022-12-23 04:51:57', 1923.01137226, 1928.48828367,
    1951.85654284, 1874.93608795, 0.0898,
    -0.2848, -2.56, 'TIME_EXIT', 10.87,
    0, '1h', '2026-03-08T18:36:22.476431'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2848,
    pnl_amount = -2.56,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DFD205E2E85FC305', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2022-12-25 06:00:00', '2022-12-25 08:02:01', 3296.89964813, 3275.93522421,
    3346.35314285, 3214.47715692, 0.0947,
    0.6359, 6.02, 'TAKE_PROFIT', 2.03,
    1, '1h', '2026-03-08T18:36:22.480387'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6359,
    pnl_amount = 6.02,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '91BDA5EE51649E2F', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-12-27 03:00:00', '2022-12-27 12:57:37', 8905.0481533, 8940.98059272,
    8771.472431, 9127.67435713, 0.102,
    0.4035, 4.11, 'TRAILING_STOP', 9.96,
    1, '1h', '2026-03-08T18:36:22.482017'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4035,
    pnl_amount = 4.11,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '24990993D3FD60D8', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-12-29 16:00:00', '2022-12-29 21:35:45', 1664.04329682, 1659.53556123,
    1639.08264737, 1705.64437924, 0.0811,
    -0.2709, -2.2, 'TIME_EXIT', 5.6,
    0, '1h', '2026-03-08T18:36:22.479629'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2709,
    pnl_amount = -2.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A8980B384336CE43', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2022-12-30 07:00:00', '2022-12-30 18:15:58', 20952.58626084, 21029.11607256,
    20638.29746692, 21476.40091736, 0.0864,
    0.3653, 3.16, 'TRAILING_STOP', 11.27,
    1, '1h', '2026-03-08T18:36:22.477803'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3653,
    pnl_amount = 3.16,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DAC7FE27EBEA63B9', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2022-12-30 19:00:00', '2022-12-30 21:47:30', 20.37655146, 20.31632018,
    20.07090319, 20.88596525, 0.0824,
    -0.2956, -2.44, 'TIME_EXIT', 2.79,
    0, '1h', '2026-03-08T18:36:22.478094'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2956,
    pnl_amount = -2.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7228509DE145F0FF', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2022-12-30 21:00:00', '2022-12-31 00:53:08', 2063.88430903, 2052.68546016,
    2094.84257367, 2012.28720131, 0.115,
    0.5426, 6.24, 'TAKE_PROFIT', 3.89,
    1, '1h', '2026-03-08T18:36:22.481693'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5426,
    pnl_amount = 6.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9D8DCD9540237952', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2022-12-31 11:00:00', '2022-12-31 14:37:05', 3913.72870567, 3900.80179207,
    3855.02277509, 4011.57192332, 0.0963,
    -0.3303, -3.18, 'STOP_LOSS', 3.62,
    0, '1h', '2026-03-08T18:36:22.476891'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3303,
    pnl_amount = -3.18,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1A30190ECFCE4ADD', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-01-06 10:00:00', '2023-01-06 13:21:43', 40688.82173165, 40450.34604222,
    41299.15405762, 39671.60118836, 0.0965,
    0.5861, 5.66, 'TRAILING_STOP', 3.36,
    1, '1h', '2026-03-08T18:36:22.479081'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5861,
    pnl_amount = 5.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ACCE5644F8C19E6A', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-01-06 17:00:00', '2023-01-07 00:06:33', 1021.22314284, 1017.8844451,
    1005.9047957, 1046.75372141, 0.0998,
    -0.3269, -3.26, 'STOP_LOSS', 7.11,
    0, '1h', '2026-03-08T18:36:22.477424'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3269,
    pnl_amount = -3.26,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C8C97175A35443D7', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-01-08 19:00:00', '2023-01-08 22:06:38', 4588.39169193, 4605.57883874,
    4657.21756731, 4473.68189963, 0.1065,
    -0.3746, -3.99, 'TIME_EXIT', 3.11,
    0, '1h', '2026-03-08T18:36:22.482478'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3746,
    pnl_amount = -3.99,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E0177B6503E6B1BC', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-01-09 14:00:00', '2023-01-09 19:31:15', 1286.78420711, 1291.55651468,
    1306.08597022, 1254.61460193, 0.1037,
    -0.3709, -3.85, 'TIME_EXIT', 5.52,
    0, '1h', '2026-03-08T18:36:22.480751'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3709,
    pnl_amount = -3.85,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AA07720BBF0BAE59', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2023-01-10 00:00:00', '2023-01-10 03:56:18', 3791.87527684, 3801.96307294,
    3848.753406, 3697.07839492, 0.0843,
    -0.266, -2.24, 'STOP_LOSS', 3.94,
    0, '1h', '2026-03-08T18:36:22.479037'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.266,
    pnl_amount = -2.24,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6A5CCCF64FF150EF', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-01-10 19:00:00', '2023-01-11 05:16:05', 31744.61285272, 31896.05761442,
    31268.44365993, 32538.22817404, 0.0914,
    0.4771, 4.36, 'TIME_EXIT', 10.27,
    1, '1h', '2026-03-08T18:36:22.477479'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4771,
    pnl_amount = 4.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8D9CEFC9A9C7AF91', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-01-19 06:00:00', '2023-01-19 11:19:35', 2677.327219, 2686.34318192,
    2717.48712729, 2610.39403853, 0.1025,
    -0.3368, -3.45, 'TIME_EXIT', 5.33,
    0, '1h', '2026-03-08T18:36:22.482390'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3368,
    pnl_amount = -3.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '36DCD0A5CB7EEDB9', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-01-19 12:00:00', '2023-01-19 19:52:42', 30003.75525883, 29891.6547706,
    29553.69892995, 30753.8491403, 0.0906,
    -0.3736, -3.38, 'TIME_EXIT', 7.88,
    0, '1h', '2026-03-08T18:36:22.483590'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3736,
    pnl_amount = -3.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C3E48788778644E5', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-01-19 23:00:00', '2023-01-20 01:33:36', 595.08561172, 597.03795175,
    604.0118959, 580.20847143, 0.1007,
    -0.3281, -3.3, 'STOP_LOSS', 2.56,
    0, '1h', '2026-03-08T18:36:22.476696'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3281,
    pnl_amount = -3.3,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '306C1B8239E330FF', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-01-21 22:00:00', '2023-01-22 07:01:29', 31956.84415317, 31840.51822677,
    32436.19681546, 31157.92304934, 0.0883,
    0.364, 3.22, 'TIME_EXIT', 9.02,
    1, '1h', '2026-03-08T18:36:22.480642'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.364,
    pnl_amount = 3.22,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E74135D8077AE28A', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2023-01-25 15:00:00', '2023-01-25 19:16:41', 3513.80888432, 3523.07719915,
    3566.51601758, 3425.96366221, 0.1107,
    -0.2638, -2.92, 'STOP_LOSS', 4.28,
    0, '1h', '2026-03-08T18:36:22.476882'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2638,
    pnl_amount = -2.92,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B2D0703BA4E595CF', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-01-27 08:00:00', '2023-01-27 14:43:30', 3098.28655776, 3116.11289418,
    3051.8122594, 3175.74372171, 0.0997,
    0.5754, 5.74, 'TAKE_PROFIT', 6.73,
    1, '1h', '2026-03-08T18:36:22.481850'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5754,
    pnl_amount = 5.74,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7089AB8BAB29A66B', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-01-29 00:00:00', '2023-01-29 07:49:24', 710.34993803, 705.74730499,
    721.0051871, 692.59118957, 0.1117,
    0.6479, 7.23, 'TIME_EXIT', 7.82,
    1, '1h', '2026-03-08T18:36:22.480119'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6479,
    pnl_amount = 7.23,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1AF16E3BB0BB719A', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-01-29 18:00:00', '2023-01-30 04:46:12', 42088.44938776, 42206.16254232,
    42719.77612857, 41036.23815306, 0.1184,
    -0.2797, -3.31, 'STOP_LOSS', 10.77,
    0, '1h', '2026-03-08T18:36:22.482756'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2797,
    pnl_amount = -3.31,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '67AE262A0D00939E', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2023-02-04 22:00:00', '2023-02-05 03:05:56', 4228.98039543, 4212.14982191,
    4292.41510136, 4123.25588554, 0.0888,
    0.398, 3.54, 'TIME_EXIT', 5.1,
    1, '1h', '2026-03-08T18:36:22.483765'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.398,
    pnl_amount = 3.54,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8D45FD01E8E9C3E6', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2023-02-07 20:00:00', '2023-02-08 05:19:30', 1722.44796503, 1717.07325317,
    1696.61124555, 1765.50916415, 0.1081,
    -0.312, -3.37, 'STOP_LOSS', 9.33,
    0, '1h', '2026-03-08T18:36:22.483908'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.312,
    pnl_amount = -3.37,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7B7CA4D812EF0974', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-02-08 07:00:00', '2023-02-08 11:45:36', 19904.72557949, 19824.20539377,
    20203.29646318, 19407.10744, 0.0839,
    0.4045, 3.39, 'TIME_EXIT', 4.76,
    1, '1h', '2026-03-08T18:36:22.479916'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4045,
    pnl_amount = 3.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CA735CE3358D6432', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2023-02-12 05:00:00', '2023-02-12 14:16:23', 3046.27041993, 3054.18946721,
    3091.96447623, 2970.11365943, 0.1166,
    -0.26, -3.03, 'STOP_LOSS', 9.27,
    0, '1h', '2026-03-08T18:36:22.481324'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.26,
    pnl_amount = -3.03,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '41A07AFE7BFC98BD', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-02-14 15:00:00', '2023-02-14 19:19:56', 4297.73204697, 4319.30612149,
    4233.26606627, 4405.17534814, 0.097,
    0.502, 4.87, 'TIME_EXIT', 4.33,
    1, '1h', '2026-03-08T18:36:22.480167'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.502,
    pnl_amount = 4.87,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F3785BA807394017', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-02-17 04:00:00', '2023-02-17 15:38:26', 19252.12341393, 19182.67703934,
    18963.34156272, 19733.42649928, 0.1112,
    -0.3607, -4.01, 'TIME_EXIT', 11.64,
    0, '1h', '2026-03-08T18:36:22.481005'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3607,
    pnl_amount = -4.01,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B4592187EC92ACC5', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2023-02-17 19:00:00', '2023-02-17 22:28:44', 1973.7231833, 1968.16240942,
    1944.11733555, 2023.06626289, 0.0908,
    -0.2817, -2.56, 'STOP_LOSS', 3.48,
    0, '1h', '2026-03-08T18:36:22.480035'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2817,
    pnl_amount = -2.56,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FFD59E4587462DCD', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2023-02-17 22:00:00', '2023-02-18 06:26:56', 2455.79556574, 2442.48194634,
    2492.63249923, 2394.4006766, 0.1027,
    0.5421, 5.57, 'TIME_EXIT', 8.45,
    1, '1h', '2026-03-08T18:36:22.478504'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5421,
    pnl_amount = 5.57,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '18F834833BDC52E3', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2023-02-21 00:00:00', '2023-02-21 05:30:14', 4486.91648368, 4456.46338944,
    4554.22023094, 4374.74357159, 0.1084,
    0.6787, 7.36, 'TRAILING_STOP', 5.5,
    1, '1h', '2026-03-08T18:36:22.481795'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6787,
    pnl_amount = 7.36,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '31E38524E16D2C70', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2023-02-24 09:00:00', '2023-02-24 13:28:02', 2813.95143758, 2826.91455333,
    2771.74216602, 2884.30022352, 0.1091,
    0.4607, 5.03, 'TRAILING_STOP', 4.47,
    1, '1h', '2026-03-08T18:36:22.479348'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4607,
    pnl_amount = 5.03,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9594702ADD3F02DC', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2023-02-25 01:00:00', '2023-02-25 06:53:15', 144.63377271, 145.30320806,
    142.46426612, 148.24961702, 0.1167,
    0.4628, 5.4, 'TAKE_PROFIT', 5.89,
    1, '1h', '2026-03-08T18:36:22.478650'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4628,
    pnl_amount = 5.4,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '26CDC5ED90F67DCE', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-02-26 10:00:00', '2023-02-26 14:17:20', 3722.67142951, 3712.07832804,
    3666.83135807, 3815.73821525, 0.1094,
    -0.2846, -3.11, 'TIME_EXIT', 4.29,
    0, '1h', '2026-03-08T18:36:22.476117'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2846,
    pnl_amount = -3.11,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D10AEB3E8F07B51C', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2023-02-27 10:00:00', '2023-02-27 19:38:00', 474.05566326, 472.25297404,
    466.94482831, 485.90705484, 0.1087,
    -0.3803, -4.13, 'TIME_EXIT', 9.63,
    0, '1h', '2026-03-08T18:36:22.484105'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3803,
    pnl_amount = -4.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8307777924353722', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2023-03-01 10:00:00', '2023-03-01 20:16:31', 403.7358489, 405.39642989,
    397.67981117, 413.82924512, 0.0806,
    0.4113, 3.31, 'TIME_EXIT', 10.28,
    1, '1h', '2026-03-08T18:36:22.479321'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4113,
    pnl_amount = 3.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A537CD7786CEB146', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-03-01 17:00:00', '2023-03-01 22:56:25', 1080.11843574, 1074.19492279,
    1096.32021227, 1053.11547485, 0.0938,
    0.5484, 5.14, 'TIME_EXIT', 5.94,
    1, '1h', '2026-03-08T18:36:22.476938'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5484,
    pnl_amount = 5.14,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B46FFD75D1788BEA', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-03-02 17:00:00', '2023-03-02 21:54:13', 488.10807124, 490.39958148,
    480.78645017, 500.31077302, 0.1111,
    0.4695, 5.22, 'TAKE_PROFIT', 4.9,
    1, '1h', '2026-03-08T18:36:22.476361'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4695,
    pnl_amount = 5.22,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '696CDE38529D3C49', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-03-03 23:00:00', '2023-03-04 04:34:04', 1366.87136955, 1357.64542375,
    1387.37444009, 1332.69958531, 0.1012,
    0.675, 6.83, 'TIME_EXIT', 5.57,
    1, '1h', '2026-03-08T18:36:22.477914'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.675,
    pnl_amount = 6.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A0A4F303A67B98BB', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2023-03-05 20:00:00', '2023-03-06 07:22:38', 412.32465792, 409.50996465,
    418.50952779, 402.01654147, 0.1057,
    0.6826, 7.22, 'TAKE_PROFIT', 11.38,
    1, '1h', '2026-03-08T18:36:22.480596'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6826,
    pnl_amount = 7.22,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9E9EB416FFF90C1D', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-03-11 19:00:00', '2023-03-12 01:15:46', 3743.30242288, 3733.03643976,
    3687.15288653, 3836.88498345, 0.0821,
    -0.2742, -2.25, 'TIME_EXIT', 6.26,
    0, '1h', '2026-03-08T18:36:22.475972'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2742,
    pnl_amount = -2.25,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1C3002CB45917399', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-03-12 09:00:00', '2023-03-12 18:47:44', 3054.37922917, 3063.08056819,
    3100.19491761, 2978.01974844, 0.0982,
    -0.2849, -2.8, 'STOP_LOSS', 9.8,
    0, '1h', '2026-03-08T18:36:22.482629'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2849,
    pnl_amount = -2.8,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AFC68997C16A379B', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-03-13 08:00:00', '2023-03-13 17:38:53', 44898.51632855, 44690.8500812,
    45571.99407347, 43776.05342033, 0.099,
    0.4625, 4.58, 'TAKE_PROFIT', 9.65,
    1, '1h', '2026-03-08T18:36:22.483285'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4625,
    pnl_amount = 4.58,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7503B982472C6A82', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2023-03-17 10:00:00', '2023-03-17 16:54:56', 4374.53476721, 4352.34079603,
    4440.15278872, 4265.17139803, 0.0983,
    0.5073, 4.99, 'TAKE_PROFIT', 6.92,
    1, '1h', '2026-03-08T18:36:22.477587'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5073,
    pnl_amount = 4.99,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '40E827CF257D6657', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-03-19 04:00:00', '2023-03-19 11:29:42', 986.58030038, 983.6052436,
    971.78159588, 1011.24480789, 0.1133,
    -0.3016, -3.42, 'STOP_LOSS', 7.5,
    0, '1h', '2026-03-08T18:36:22.478248'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3016,
    pnl_amount = -3.42,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3F3E729C4841031C', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-03-24 04:00:00', '2023-03-24 12:45:59', 108.40715396, 107.89375439,
    110.03326127, 105.69697511, 0.0952,
    0.4736, 4.51, 'TRAILING_STOP', 8.77,
    1, '1h', '2026-03-08T18:36:22.477103'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4736,
    pnl_amount = 4.51,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '40D14F169BFEB36A', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-03-24 23:00:00', '2023-03-25 01:53:22', 3961.23611465, 3985.97235696,
    3901.81757293, 4060.26701752, 0.0971,
    0.6245, 6.06, 'TIME_EXIT', 2.89,
    1, '1h', '2026-03-08T18:36:22.476966'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6245,
    pnl_amount = 6.06,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '445D7552C3C4F6B2', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-03-25 05:00:00', '2023-03-25 13:12:18', 245.39511291, 246.18971529,
    249.07603961, 239.26023509, 0.1134,
    -0.3238, -3.67, 'STOP_LOSS', 8.21,
    0, '1h', '2026-03-08T18:36:22.484001'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3238,
    pnl_amount = -3.67,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '91CCA6B22E5CEF06', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-03-27 17:00:00', '2023-03-28 00:25:03', 6413.73176868, 6369.91870423,
    6509.93774521, 6253.38847446, 0.0874,
    0.6831, 5.97, 'TAKE_PROFIT', 7.42,
    1, '1h', '2026-03-08T18:36:22.475953'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6831,
    pnl_amount = 5.97,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D83F864236501252', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2023-04-07 12:00:00', '2023-04-07 18:25:45', 4807.87358186, 4820.5544986,
    4879.99168559, 4687.67674231, 0.1023,
    -0.2638, -2.7, 'STOP_LOSS', 6.43,
    0, '1h', '2026-03-08T18:36:22.479366'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2638,
    pnl_amount = -2.7,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '55A109ED53FC56AF', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2023-04-15 15:00:00', '2023-04-15 21:31:15', 112.40847459, 111.97934511,
    110.72234747, 115.21868645, 0.1122,
    -0.3818, -4.28, 'STOP_LOSS', 6.52,
    0, '1h', '2026-03-08T18:36:22.478280'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3818,
    pnl_amount = -4.28,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F15F666E2649B10D', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2023-04-16 14:00:00', '2023-04-16 17:09:47', 1017.45795061, 1011.49387875,
    1032.71981986, 992.02150184, 0.1013,
    0.5862, 5.94, 'TIME_EXIT', 3.16,
    1, '1h', '2026-03-08T18:36:22.481921'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5862,
    pnl_amount = 5.94,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ABA134F20A473E41', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-04-19 08:00:00', '2023-04-19 16:17:32', 30794.58729503, 30592.14600287,
    31256.50610446, 30024.72261266, 0.1038,
    0.6574, 6.82, 'TRAILING_STOP', 8.29,
    1, '1h', '2026-03-08T18:36:22.481064'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6574,
    pnl_amount = 6.82,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD578B7A4EBF9744', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-04-22 16:00:00', '2023-04-22 19:51:59', 36579.7225654, 36780.38287414,
    36031.02672692, 37494.21562953, 0.1105,
    0.5486, 6.06, 'TRAILING_STOP', 3.87,
    1, '1h', '2026-03-08T18:36:22.481523'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5486,
    pnl_amount = 6.06,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3E40C67F6F11D663', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-04-23 00:00:00', '2023-04-23 05:35:25', 3796.92261096, 3775.40699902,
    3853.87645013, 3701.99954569, 0.0988,
    0.5667, 5.6, 'TRAILING_STOP', 5.59,
    1, '1h', '2026-03-08T18:36:22.479842'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5667,
    pnl_amount = 5.6,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A3E44BC2199038FE', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-04-25 00:00:00', '2023-04-25 05:49:38', 3723.86958622, 3697.85754247,
    3779.72763001, 3630.77284656, 0.082,
    0.6985, 5.73, 'TRAILING_STOP', 5.83,
    1, '1h', '2026-03-08T18:36:22.480405'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6985,
    pnl_amount = 5.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C33FE0010F08056C', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-04-25 09:00:00', '2023-04-25 13:49:06', 1134.44242072, 1130.11969135,
    1117.42578441, 1162.80348124, 0.0939,
    -0.381, -3.58, 'STOP_LOSS', 4.82,
    0, '1h', '2026-03-08T18:36:22.484062'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.381,
    pnl_amount = -3.58,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9BED277CF6DADA7B', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2023-04-30 03:00:00', '2023-04-30 09:41:09', 4277.75550141, 4263.38380589,
    4213.58916888, 4384.69938894, 0.0992,
    -0.336, -3.33, 'TIME_EXIT', 6.69,
    0, '1h', '2026-03-08T18:36:22.483897'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.336,
    pnl_amount = -3.33,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2648551775DC7598', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-04-30 21:00:00', '2023-05-01 02:46:17', 1461.73972885, 1470.05389482,
    1439.81363292, 1498.28322207, 0.1173,
    0.5688, 6.67, 'TAKE_PROFIT', 5.77,
    1, '1h', '2026-03-08T18:36:22.478363'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5688,
    pnl_amount = 6.67,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B76DA5BA4019E90B', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2023-05-01 02:00:00', '2023-05-01 10:50:55', 1842.45844827, 1847.39689937,
    1870.09532499, 1796.39698706, 0.0816,
    -0.268, -2.19, 'TIME_EXIT', 8.85,
    0, '1h', '2026-03-08T18:36:22.478838'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.268,
    pnl_amount = -2.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A4C1E2611921140F', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-05-01 18:00:00', '2023-05-02 04:42:40', 4733.60365857, 4718.48086703,
    4662.59960369, 4851.94375003, 0.0885,
    -0.3195, -2.83, 'STOP_LOSS', 10.71,
    0, '1h', '2026-03-08T18:36:22.482554'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3195,
    pnl_amount = -2.83,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '61B533BAD3610803', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-05-02 01:00:00', '2023-05-02 09:45:17', 2399.28698039, 2411.53956179,
    2363.29767569, 2459.2691549, 0.0884,
    0.5107, 4.52, 'TAKE_PROFIT', 8.75,
    1, '1h', '2026-03-08T18:36:22.480632'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5107,
    pnl_amount = 4.52,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CC9BC1EC0E4DE6C7', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2023-05-02 20:00:00', '2023-05-02 22:48:11', 2601.37188373, 2591.51432274,
    2640.39246199, 2536.33758664, 0.1172,
    0.3789, 4.44, 'TIME_EXIT', 2.8,
    1, '1h', '2026-03-08T18:36:22.481611'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3789,
    pnl_amount = 4.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B194D02E4E5E8B4E', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-05-05 06:00:00', '2023-05-05 15:44:21', 2389.29287737, 2396.52289266,
    2425.13227053, 2329.56055544, 0.1081,
    -0.3026, -3.27, 'TIME_EXIT', 9.74,
    0, '1h', '2026-03-08T18:36:22.480827'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3026,
    pnl_amount = -3.27,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C2093F47C27DBD8E', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2023-05-06 18:00:00', '2023-05-07 03:53:39', 4977.64018359, 4992.81766094,
    5052.30478634, 4853.199179, 0.1177,
    -0.3049, -3.59, 'TIME_EXIT', 9.89,
    0, '1h', '2026-03-08T18:36:22.478956'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3049,
    pnl_amount = -3.59,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '100B44E3FFB175EF', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2023-05-06 18:00:00', '2023-05-07 03:29:39', 1105.03817939, 1109.05665305,
    1088.4626067, 1132.66413387, 0.1189,
    0.3637, 4.33, 'TIME_EXIT', 9.49,
    1, '1h', '2026-03-08T18:36:22.480091'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3637,
    pnl_amount = 4.33,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '36CF6FF016289712', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-05-14 10:00:00', '2023-05-14 14:46:38', 3360.29484607, 3377.87281604,
    3309.89042338, 3444.30221722, 0.0893,
    0.5231, 4.67, 'TAKE_PROFIT', 4.78,
    1, '1h', '2026-03-08T18:36:22.481665'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5231,
    pnl_amount = 4.67,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9291063BC539FA43', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-05-14 13:00:00', '2023-05-14 23:10:44', 1593.60853149, 1588.70245206,
    1569.70440352, 1633.44874478, 0.0938,
    -0.3079, -2.89, 'STOP_LOSS', 10.18,
    0, '1h', '2026-03-08T18:36:22.478793'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3079,
    pnl_amount = -2.89,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9769EF0FCA66FF71', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-05-17 02:00:00', '2023-05-17 05:49:49', 33449.93110801, 33656.68291093,
    32948.18214139, 34286.17938571, 0.0913,
    0.6181, 5.64, 'TIME_EXIT', 3.83,
    1, '1h', '2026-03-08T18:36:22.481129'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6181,
    pnl_amount = 5.64,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C0B1351BFA12BDBF', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2023-05-20 01:00:00', '2023-05-20 04:38:54', 875.86973291, 879.22726618,
    862.73168692, 897.76647623, 0.109,
    0.3833, 4.18, 'TAKE_PROFIT', 3.65,
    1, '1h', '2026-03-08T18:36:22.481248'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3833,
    pnl_amount = 4.18,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '996B9F4174855FE9', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-05-22 03:00:00', '2023-05-22 05:26:03', 3797.05773906, 3819.32522017,
    3740.10187297, 3891.98418254, 0.0977,
    0.5864, 5.73, 'TRAILING_STOP', 2.43,
    1, '1h', '2026-03-08T18:36:22.479801'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5864,
    pnl_amount = 5.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F8C82C880B590018', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-05-23 03:00:00', '2023-05-23 13:36:19', 897.9187309, 901.26634638,
    884.44994994, 920.36669917, 0.1183,
    0.3728, 4.41, 'TIME_EXIT', 10.61,
    1, '1h', '2026-03-08T18:36:22.478848'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3728,
    pnl_amount = 4.41,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '48BC518D26419D77', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-05-24 02:00:00', '2023-05-24 06:15:25', 1798.64565592, 1790.17915701,
    1825.62534076, 1753.67951453, 0.0843,
    0.4707, 3.97, 'TAKE_PROFIT', 4.26,
    1, '1h', '2026-03-08T18:36:22.476957'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4707,
    pnl_amount = 3.97,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7A4C13542709E8D4', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2023-05-27 00:00:00', '2023-05-27 11:41:40', 3789.66788928, 3766.89909395,
    3846.51290762, 3694.92619205, 0.0882,
    0.6008, 5.3, 'TIME_EXIT', 11.69,
    1, '1h', '2026-03-08T18:36:22.476621'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6008,
    pnl_amount = 5.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '23EAC1FCF292D9FE', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-05-29 07:00:00', '2023-05-29 14:31:44', 14634.65100307, 14710.91003397,
    14415.13123802, 15000.51727815, 0.1087,
    0.5211, 5.67, 'TIME_EXIT', 7.53,
    1, '1h', '2026-03-08T18:36:22.482171'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5211,
    pnl_amount = 5.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '14FE5279A4A663A2', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-06-05 00:00:00', '2023-06-05 03:27:28', 1762.27002626, 1766.90643409,
    1788.70407666, 1718.2132756, 0.0938,
    -0.2631, -2.47, 'STOP_LOSS', 3.46,
    0, '1h', '2026-03-08T18:36:22.477728'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2631,
    pnl_amount = -2.47,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5A982406EAB5724D', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2023-06-06 14:00:00', '2023-06-06 22:13:09', 2451.94617437, 2437.84466103,
    2488.72536698, 2390.64752001, 0.0832,
    0.5751, 4.78, 'TRAILING_STOP', 8.22,
    1, '1h', '2026-03-08T18:36:22.481989'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5751,
    pnl_amount = 4.78,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FFC386BB32727860', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2023-06-08 08:00:00', '2023-06-08 18:27:57', 4763.67288385, 4738.78132591,
    4835.12797711, 4644.58106175, 0.0903,
    0.5225, 4.72, 'TIME_EXIT', 10.47,
    1, '1h', '2026-03-08T18:36:22.475943'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5225,
    pnl_amount = 4.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FA46CCBDB0BA4E0A', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-06-08 09:00:00', '2023-06-08 14:47:58', 4971.062968, 4989.41074477,
    5045.62891252, 4846.7863938, 0.1098,
    -0.3691, -4.05, 'TIME_EXIT', 5.8,
    0, '1h', '2026-03-08T18:36:22.477904'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3691,
    pnl_amount = -4.05,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C282F81C594F201', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2023-06-09 17:00:00', '2023-06-10 03:26:47', 2861.14809596, 2869.8915201,
    2904.0653174, 2789.61939356, 0.102,
    -0.3056, -3.12, 'STOP_LOSS', 10.45,
    0, '1h', '2026-03-08T18:36:22.478966'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3056,
    pnl_amount = -3.12,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '04C4D2E06373D55B', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-06-09 22:00:00', '2023-06-10 01:35:28', 395.22887843, 396.67434036,
    389.30044525, 405.10960039, 0.1008,
    0.3657, 3.69, 'TAKE_PROFIT', 3.59,
    1, '1h', '2026-03-08T18:36:22.477003'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3657,
    pnl_amount = 3.69,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A7866CD4FBDA64E', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-06-17 02:00:00', '2023-06-17 10:21:16', 7673.49134331, 7725.80691727,
    7558.38897316, 7865.32862689, 0.1049,
    0.6818, 7.15, 'TIME_EXIT', 8.35,
    1, '1h', '2026-03-08T18:36:22.478633'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6818,
    pnl_amount = 7.15,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C271E85A99FD4B67', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2023-06-18 21:00:00', '2023-06-19 00:37:52', 3530.89933341, 3550.89164854,
    3477.93584341, 3619.17181674, 0.1136,
    0.5662, 6.43, 'TIME_EXIT', 3.63,
    1, '1h', '2026-03-08T18:36:22.476331'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5662,
    pnl_amount = 6.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F2A945DC9A86E8D9', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-06-19 04:00:00', '2023-06-19 09:02:17', 4405.51221684, 4417.29129957,
    4471.5949001, 4295.37441142, 0.1166,
    -0.2674, -3.12, 'TIME_EXIT', 5.04,
    0, '1h', '2026-03-08T18:36:22.478715'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2674,
    pnl_amount = -3.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0E06DBE2CB9CBF43', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2023-06-20 02:00:00', '2023-06-20 12:21:43', 2444.14604932, 2428.08125872,
    2480.80824006, 2383.04239809, 0.111,
    0.6573, 7.3, 'TAKE_PROFIT', 10.36,
    1, '1h', '2026-03-08T18:36:22.478513'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6573,
    pnl_amount = 7.3,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F48C2F10B3D38055', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-06-24 11:00:00', '2023-06-24 15:49:57', 314.82266234, 313.9622302,
    310.10032241, 322.6932289, 0.0916,
    -0.2733, -2.5, 'STOP_LOSS', 4.83,
    0, '1h', '2026-03-08T18:36:22.480732'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2733,
    pnl_amount = -2.5,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D1782DA20EE02E48', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2023-06-27 10:00:00', '2023-06-27 13:45:56', 1444.44695018, 1437.77785772,
    1466.11365443, 1408.33577642, 0.0934,
    0.4617, 4.31, 'TRAILING_STOP', 3.77,
    1, '1h', '2026-03-08T18:36:22.478431'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4617,
    pnl_amount = 4.31,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '32FE0660256778CE', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2023-06-30 23:00:00', '2023-07-01 10:26:11', 4665.55854051, 4693.92978721,
    4595.5751624, 4782.19750402, 0.0885,
    0.6081, 5.38, 'TIME_EXIT', 11.44,
    1, '1h', '2026-03-08T18:36:22.479054'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6081,
    pnl_amount = 5.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '422ACE43DAA72F49', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-07-01 23:00:00', '2023-07-02 09:09:52', 3183.76887857, 3161.78546023,
    3231.52541175, 3104.17465661, 0.1011,
    0.6905, 6.98, 'TRAILING_STOP', 10.16,
    1, '1h', '2026-03-08T18:36:22.483544'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6905,
    pnl_amount = 6.98,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5D5B054A44DDF204', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-07-02 21:00:00', '2023-07-03 08:12:07', 3796.7492835, 3786.15985224,
    3739.79804425, 3891.66801559, 0.0842,
    -0.2789, -2.35, 'STOP_LOSS', 11.2,
    0, '1h', '2026-03-08T18:36:22.481565'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2789,
    pnl_amount = -2.35,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1D60268496F5D96D', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2023-07-04 09:00:00', '2023-07-04 17:44:57', 87.89438376, 87.58231932,
    86.57596801, 90.09174336, 0.0829,
    -0.355, -2.94, 'TIME_EXIT', 8.75,
    0, '1h', '2026-03-08T18:36:22.483936'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.355,
    pnl_amount = -2.94,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '53B1E0F5466E29D4', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-07-06 12:00:00', '2023-07-06 14:34:41', 19833.27858927, 19768.99900093,
    19535.77941043, 20329.110554, 0.1109,
    -0.3241, -3.6, 'STOP_LOSS', 2.58,
    0, '1h', '2026-03-08T18:36:22.481740'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3241,
    pnl_amount = -3.6,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F9C50756C1817103', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-07-07 15:00:00', '2023-07-08 01:28:31', 767.74381924, 771.49951171,
    756.22766195, 786.93741472, 0.1099,
    0.4892, 5.38, 'TRAILING_STOP', 10.48,
    1, '1h', '2026-03-08T18:36:22.478422'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4892,
    pnl_amount = 5.38,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '340D18428E1C5B3E', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-07-08 13:00:00', '2023-07-08 17:35:21', 3598.34771337, 3576.79984467,
    3652.32292907, 3508.38902054, 0.1128,
    0.5988, 6.75, 'TRAILING_STOP', 4.59,
    1, '1h', '2026-03-08T18:36:22.482498'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5988,
    pnl_amount = 6.75,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AB1AFFFE2FFFCBFB', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-07-10 02:00:00', '2023-07-10 07:37:42', 2686.16485655, 2676.57106066,
    2726.4573294, 2619.01073514, 0.0973,
    0.3572, 3.48, 'TRAILING_STOP', 5.63,
    1, '1h', '2026-03-08T18:36:22.480958'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3572,
    pnl_amount = 3.48,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2943A785753E8D47', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-07-11 05:00:00', '2023-07-11 16:44:54', 2987.0497804, 2976.57108557,
    2942.2440337, 3061.72602491, 0.0952,
    -0.3508, -3.34, 'TIME_EXIT', 11.75,
    0, '1h', '2026-03-08T18:36:22.478289'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3508,
    pnl_amount = -3.34,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '171FECF109D234F1', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-07-13 21:00:00', '2023-07-14 01:57:10', 3958.90244129, 3938.56980594,
    4018.28597791, 3859.92988025, 0.0989,
    0.5136, 5.08, 'TAKE_PROFIT', 4.95,
    1, '1h', '2026-03-08T18:36:22.481147'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5136,
    pnl_amount = 5.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AE48B3A6D48D7DEA', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-07-25 11:00:00', '2023-07-25 15:37:04', 27551.58187123, 27676.86339946,
    27138.30814316, 28240.37141801, 0.0806,
    0.4547, 3.66, 'TRAILING_STOP', 4.62,
    1, '1h', '2026-03-08T18:36:22.477094'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4547,
    pnl_amount = 3.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B63E539078471255', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-07-26 05:00:00', '2023-07-26 08:15:04', 1149.00893523, 1154.48264786,
    1131.7738012, 1177.73415861, 0.1182,
    0.4764, 5.63, 'TAKE_PROFIT', 3.25,
    1, '1h', '2026-03-08T18:36:22.483221'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4764,
    pnl_amount = 5.63,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E2575990E41DDE0F', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2023-07-26 15:00:00', '2023-07-26 20:51:18', 82.1151985, 82.43011893,
    80.88347052, 84.16807846, 0.0905,
    0.3835, 3.47, 'TAKE_PROFIT', 5.86,
    1, '1h', '2026-03-08T18:36:22.481555'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3835,
    pnl_amount = 3.47,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7DA3FC9155F74820', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2023-07-26 20:00:00', '2023-07-26 22:37:22', 749.66885119, 753.60411683,
    738.42381843, 768.41057247, 0.1082,
    0.5249, 5.68, 'TIME_EXIT', 2.62,
    1, '1h', '2026-03-08T18:36:22.477415'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5249,
    pnl_amount = 5.68,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '20478735A9DAF1DF', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2023-07-27 15:00:00', '2023-07-27 18:29:32', 3405.4382373, 3423.87577115,
    3354.35666374, 3490.57419323, 0.0889,
    0.5414, 4.82, 'TIME_EXIT', 3.49,
    1, '1h', '2026-03-08T18:36:22.476683'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5414,
    pnl_amount = 4.82,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FA5B928B66FA55DB', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-07-28 07:00:00', '2023-07-28 10:03:48', 88.66711866, 88.24735359,
    89.99712544, 86.4504407, 0.0843,
    0.4734, 3.99, 'TAKE_PROFIT', 3.06,
    1, '1h', '2026-03-08T18:36:22.476352'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4734,
    pnl_amount = 3.99,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4AC10F5DE8CF29E9', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2023-07-28 18:00:00', '2023-07-29 03:38:16', 1230.03973626, 1224.98555752,
    1248.4903323, 1199.28874285, 0.1196,
    0.4109, 4.91, 'TAKE_PROFIT', 9.64,
    1, '1h', '2026-03-08T18:36:22.477950'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4109,
    pnl_amount = 4.91,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C74280DE870C73ED', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2023-07-29 09:00:00', '2023-07-29 19:43:42', 2497.0476327, 2484.93313041,
    2534.50334719, 2434.62144188, 0.0882,
    0.4852, 4.28, 'TRAILING_STOP', 10.73,
    1, '1h', '2026-03-08T18:36:22.481767'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4852,
    pnl_amount = 4.28,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C8799635D50C7B8E', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-07-30 23:00:00', '2023-07-31 02:06:33', 222.20574277, 223.60806037,
    218.87265663, 227.76088634, 0.1019,
    0.6311, 6.43, 'TRAILING_STOP', 3.11,
    1, '1h', '2026-03-08T18:36:22.476313'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6311,
    pnl_amount = 6.43,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '16F87003B23F47BC', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2023-08-05 09:00:00', '2023-08-05 18:05:08', 3426.36476446, 3416.28699349,
    3374.96929299, 3512.02388357, 0.1063,
    -0.2941, -3.13, 'TIME_EXIT', 9.09,
    0, '1h', '2026-03-08T18:36:22.477231'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2941,
    pnl_amount = -3.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98FCEB6253B248E4', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-08-06 08:00:00', '2023-08-06 17:21:36', 1520.0592493, 1511.46802144,
    1542.86013804, 1482.05776807, 0.0959,
    0.5652, 5.42, 'TRAILING_STOP', 9.36,
    1, '1h', '2026-03-08T18:36:22.479124'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5652,
    pnl_amount = 5.42,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '79D69B23F79EC60D', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-08-06 17:00:00', '2023-08-06 19:44:28', 3224.92932044, 3212.64536457,
    3273.30326025, 3144.30608743, 0.0952,
    0.3809, 3.62, 'TRAILING_STOP', 2.74,
    1, '1h', '2026-03-08T18:36:22.478235'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3809,
    pnl_amount = 3.62,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9DF9A11CEE2C3147', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2023-08-07 23:00:00', '2023-08-08 05:59:29', 2411.20740271, 2404.83378605,
    2375.03929167, 2471.48758777, 0.109,
    -0.2643, -2.88, 'STOP_LOSS', 6.99,
    0, '1h', '2026-03-08T18:36:22.483394'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2643,
    pnl_amount = -2.88,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D12ABDD16D0D2938', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-08-08 01:00:00', '2023-08-08 07:10:16', 39292.46016668, 39031.68899845,
    39881.84706918, 38310.14866251, 0.0847,
    0.6637, 5.62, 'TAKE_PROFIT', 6.17,
    1, '1h', '2026-03-08T18:36:22.481337'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6637,
    pnl_amount = 5.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7493446A195DF525', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-08-11 20:00:00', '2023-08-12 03:20:23', 273.04122484, 274.77118734,
    268.94560646, 279.86725546, 0.0811,
    0.6336, 5.14, 'TAKE_PROFIT', 7.34,
    1, '1h', '2026-03-08T18:36:22.477997'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6336,
    pnl_amount = 5.14,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8BF82DB3F4684EFE', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2023-08-13 15:00:00', '2023-08-14 01:04:16', 4699.99477322, 4729.49258184,
    4629.49485162, 4817.49464255, 0.1036,
    0.6276, 6.5, 'TIME_EXIT', 10.07,
    1, '1h', '2026-03-08T18:36:22.483096'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6276,
    pnl_amount = 6.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DF7EFD55B0EF4FE1', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-08-18 19:00:00', '2023-08-19 02:44:49', 21381.09145323, 21299.58941872,
    21060.37508143, 21915.61873956, 0.1022,
    -0.3812, -3.9, 'STOP_LOSS', 7.75,
    0, '1h', '2026-03-08T18:36:22.482711'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3812,
    pnl_amount = -3.9,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0DE0BDB2CA427E1C', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-08-18 21:00:00', '2023-08-19 08:59:22', 1334.97182073, 1339.94315691,
    1354.99639804, 1301.59752521, 0.1159,
    -0.3724, -4.31, 'STOP_LOSS', 11.99,
    0, '1h', '2026-03-08T18:36:22.479647'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3724,
    pnl_amount = -4.31,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '45B701B8B4B3EB65', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-08-21 07:00:00', '2023-08-21 13:15:02', 2079.00188402, 2070.71921982,
    2110.18691228, 2027.02683692, 0.1195,
    0.3984, 4.76, 'TRAILING_STOP', 6.25,
    1, '1h', '2026-03-08T18:36:22.476612'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3984,
    pnl_amount = 4.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC495DBFC1DE26EE', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2023-08-25 23:00:00', '2023-08-26 08:57:26', 69.70334087, 69.44030057,
    68.65779076, 71.44592439, 0.0957,
    -0.3774, -3.61, 'STOP_LOSS', 9.96,
    0, '1h', '2026-03-08T18:36:22.480100'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3774,
    pnl_amount = -3.61,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '65D2868CCFA4DB8E', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-08-26 09:00:00', '2023-08-26 13:49:55', 4760.28130459, 4780.84394818,
    4688.87708502, 4879.28833721, 0.081,
    0.432, 3.5, 'TAKE_PROFIT', 4.83,
    1, '1h', '2026-03-08T18:36:22.479046'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.432,
    pnl_amount = 3.5,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '144B9D7753311D3A', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-08-26 13:00:00', '2023-08-26 21:25:16', 3723.32085563, 3736.36540857,
    3667.4710428, 3816.40387702, 0.115,
    0.3503, 4.03, 'TIME_EXIT', 8.42,
    1, '1h', '2026-03-08T18:36:22.476021'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3503,
    pnl_amount = 4.03,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '418D4504198A6C93', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-08-30 17:00:00', '2023-08-30 22:31:12', 1373.68913277, 1368.64386324,
    1353.08379577, 1408.03136108, 0.1026,
    -0.3673, -3.77, 'STOP_LOSS', 5.52,
    0, '1h', '2026-03-08T18:36:22.482516'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3673,
    pnl_amount = -3.77,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '449C68951EF62877', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2023-09-01 19:00:00', '2023-09-02 06:43:18', 2221.96760609, 2216.19472563,
    2188.638092, 2277.51679624, 0.0814,
    -0.2598, -2.11, 'STOP_LOSS', 11.72,
    0, '1h', '2026-03-08T18:36:22.478167'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2598,
    pnl_amount = -2.11,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '869674B120869BF7', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-09-08 01:00:00', '2023-09-08 09:23:35', 2954.7543421, 2941.64399457,
    2999.07565724, 2880.88548355, 0.0924,
    0.4437, 4.1, 'TRAILING_STOP', 8.39,
    1, '1h', '2026-03-08T18:36:22.479330'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4437,
    pnl_amount = 4.1,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F5EECF677CF41B95', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-09-09 16:00:00', '2023-09-10 02:52:12', 1269.48771548, 1278.00124259,
    1250.44539975, 1301.22490837, 0.0814,
    0.6706, 5.46, 'TIME_EXIT', 10.87,
    1, '1h', '2026-03-08T18:36:22.482198'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6706,
    pnl_amount = 5.46,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0FE7488BE073FCE3', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2023-09-15 20:00:00', '2023-09-16 05:48:08', 1171.51333402, 1164.20256752,
    1189.08603403, 1142.22550067, 0.0954,
    0.624, 5.95, 'TRAILING_STOP', 9.8,
    1, '1h', '2026-03-08T18:36:22.479508'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.624,
    pnl_amount = 5.95,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '518B8094AD83F881', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2023-09-21 01:00:00', '2023-09-21 12:50:51', 3917.11750306, 3942.6034581,
    3858.36074051, 4015.04544063, 0.1089,
    0.6506, 7.08, 'TIME_EXIT', 11.85,
    1, '1h', '2026-03-08T18:36:22.479424'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6506,
    pnl_amount = 7.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '74B493C198A8B4F2', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-09-23 01:00:00', '2023-09-23 04:59:46', 172.41334148, 173.59186917,
    169.82714136, 176.72367502, 0.111,
    0.6835, 7.59, 'TIME_EXIT', 4.0,
    1, '1h', '2026-03-08T18:36:22.481894'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6835,
    pnl_amount = 7.59,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FBB4DB9CA6D24888', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-09-27 23:00:00', '2023-09-28 08:15:17', 40961.43517434, 40852.01016259,
    40347.01364672, 41985.4710537, 0.1021,
    -0.2671, -2.73, 'STOP_LOSS', 9.25,
    0, '1h', '2026-03-08T18:36:22.481504'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2671,
    pnl_amount = -2.73,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BEDA129B2BDF2F9A', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-09-29 03:00:00', '2023-09-29 12:18:14', 2109.51446767, 2121.0657758,
    2077.87175066, 2162.25232937, 0.1051,
    0.5476, 5.76, 'TRAILING_STOP', 9.3,
    1, '1h', '2026-03-08T18:36:22.477148'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5476,
    pnl_amount = 5.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '38257915B39EF926', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2023-09-30 15:00:00', '2023-10-01 02:54:59', 3387.55198685, 3373.12243379,
    3438.36526665, 3302.86318718, 0.0997,
    0.426, 4.25, 'TAKE_PROFIT', 11.92,
    1, '1h', '2026-03-08T18:36:22.480370'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.426,
    pnl_amount = 4.25,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0259BD988DC83A50', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2023-10-01 09:00:00', '2023-10-01 20:20:56', 1721.5879563, 1713.93499317,
    1747.41177565, 1678.54825739, 0.088,
    0.4445, 3.91, 'TAKE_PROFIT', 11.35,
    1, '1h', '2026-03-08T18:36:22.479981'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4445,
    pnl_amount = 3.91,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3346C7A25C2BBED1', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-10-01 16:00:00', '2023-10-02 01:12:45', 2334.08774808, 2346.19083697,
    2299.07643186, 2392.43994178, 0.1051,
    0.5185, 5.45, 'TRAILING_STOP', 9.21,
    1, '1h', '2026-03-08T18:36:22.481184'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5185,
    pnl_amount = 5.45,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC483D50BB3B3B89', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-10-03 03:00:00', '2023-10-03 12:08:33', 4323.43009683, 4310.04725987,
    4258.57864538, 4431.51584925, 0.1123,
    -0.3095, -3.48, 'STOP_LOSS', 9.14,
    0, '1h', '2026-03-08T18:36:22.482046'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3095,
    pnl_amount = -3.48,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F30A06ADF29E6172', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-10-05 07:00:00', '2023-10-05 11:26:17', 882.35096232, 886.79038004,
    869.11569789, 904.40973638, 0.0931,
    0.5031, 4.69, 'TRAILING_STOP', 4.44,
    1, '1h', '2026-03-08T18:36:22.478392'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5031,
    pnl_amount = 4.69,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A1F04942F3A9F64', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2023-10-05 07:00:00', '2023-10-05 15:39:00', 3324.7567258, 3313.60344353,
    3274.88537492, 3407.87564395, 0.1038,
    -0.3355, -3.48, 'STOP_LOSS', 8.65,
    0, '1h', '2026-03-08T18:36:22.483626'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3355,
    pnl_amount = -3.48,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '86F1BB7BB034CDDF', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2023-10-12 17:00:00', '2023-10-12 22:48:54', 1441.04394332, 1437.20838655,
    1419.42828417, 1477.07004191, 0.1083,
    -0.2662, -2.88, 'TIME_EXIT', 5.82,
    0, '1h', '2026-03-08T18:36:22.480396'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2662,
    pnl_amount = -2.88,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F87AECBACAE68A7', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-10-14 18:00:00', '2023-10-15 04:54:08', 10403.21876245, 10363.71414126,
    10559.26704389, 10143.13829339, 0.1033,
    0.3797, 3.92, 'TRAILING_STOP', 10.9,
    1, '1h', '2026-03-08T18:36:22.478259'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3797,
    pnl_amount = 3.92,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '73DB256690A952E8', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-10-22 18:00:00', '2023-10-23 02:03:11', 569.66927364, 567.54561162,
    561.12423454, 583.91100548, 0.1076,
    -0.3728, -4.01, 'TIME_EXIT', 8.05,
    0, '1h', '2026-03-08T18:36:22.478877'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3728,
    pnl_amount = -4.01,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F15F15D3E38F8B47', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2023-10-24 15:00:00', '2023-10-24 22:26:08', 3908.63687057, 3891.63451132,
    3967.26642363, 3810.92094881, 0.086,
    0.435, 3.74, 'TRAILING_STOP', 7.44,
    1, '1h', '2026-03-08T18:36:22.477302'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.435,
    pnl_amount = 3.74,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '985235349ED1E7AD', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-10-25 03:00:00', '2023-10-25 11:46:58', 17.9534301, 17.89811115,
    17.68412865, 18.40226585, 0.0966,
    -0.3081, -2.98, 'STOP_LOSS', 8.78,
    0, '1h', '2026-03-08T18:36:22.480836'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3081,
    pnl_amount = -2.98,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A297D369FFBC05C4', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-10-27 08:00:00', '2023-10-27 13:09:09', 35839.19243439, 35720.47089606,
    35301.60454788, 36735.17224525, 0.0846,
    -0.3313, -2.8, 'STOP_LOSS', 5.15,
    0, '1h', '2026-03-08T18:36:22.477988'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3313,
    pnl_amount = -2.8,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30257D90C646AA36', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-10-27 20:00:00', '2023-10-28 02:37:35', 499.44866444, 501.6074092,
    491.95693447, 511.93488105, 0.0938,
    0.4322, 4.05, 'TIME_EXIT', 6.63,
    1, '1h', '2026-03-08T18:36:22.481868'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4322,
    pnl_amount = 4.05,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '25B9F8BED5856125', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2023-11-01 20:00:00', '2023-11-02 03:58:49', 77.8323916, 78.29421216,
    76.66490572, 79.77820139, 0.0924,
    0.5934, 5.48, 'TAKE_PROFIT', 7.98,
    1, '1h', '2026-03-08T18:36:22.483737'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5934,
    pnl_amount = 5.48,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2A2AF23D8609E2B8', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2023-11-02 02:00:00', '2023-11-02 09:00:12', 1354.54083545, 1347.46192929,
    1374.85894798, 1320.67731457, 0.1192,
    0.5226, 6.23, 'TAKE_PROFIT', 7.0,
    1, '1h', '2026-03-08T18:36:22.480704'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5226,
    pnl_amount = 6.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3E73AC023AD4F6FC', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2023-11-04 01:00:00', '2023-11-04 10:04:24', 3914.34934211, 3892.26318069,
    3973.06458224, 3816.49060856, 0.1077,
    0.5642, 6.08, 'TAKE_PROFIT', 9.07,
    1, '1h', '2026-03-08T18:36:22.475905'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5642,
    pnl_amount = 6.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '07E3BF792A2514E2', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-11-04 05:00:00', '2023-11-04 09:48:08', 4816.96687736, 4842.15373404,
    4744.7123742, 4937.39104929, 0.0998,
    0.5229, 5.22, 'TAKE_PROFIT', 4.8,
    1, '1h', '2026-03-08T18:36:22.476419'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5229,
    pnl_amount = 5.22,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '31D8352A6AD2ECD0', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-11-13 09:00:00', '2023-11-13 12:49:22', 1796.54059942, 1790.91610384,
    1769.59249042, 1841.4541144, 0.0881,
    -0.3131, -2.76, 'STOP_LOSS', 3.82,
    0, '1h', '2026-03-08T18:36:22.479387'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3131,
    pnl_amount = -2.76,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9D1E8F3316649B3D', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-11-15 09:00:00', '2023-11-15 19:45:46', 1573.94559693, 1579.90795359,
    1550.33641297, 1613.29423685, 0.0968,
    0.3788, 3.67, 'TAKE_PROFIT', 10.76,
    1, '1h', '2026-03-08T18:36:22.479935'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3788,
    pnl_amount = 3.67,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6B9E260BB1D77D63', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2023-11-16 17:00:00', '2023-11-17 01:50:02', 161.82545371, 161.24438949,
    159.3980719, 165.87109005, 0.1067,
    -0.3591, -3.83, 'STOP_LOSS', 8.83,
    0, '1h', '2026-03-08T18:36:22.482344'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3591,
    pnl_amount = -3.83,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B54A77746BC126DC', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2023-11-22 10:00:00', '2023-11-22 17:46:39', 2924.59645785, 2933.52408777,
    2968.46540472, 2851.4815464, 0.1118,
    -0.3053, -3.41, 'TIME_EXIT', 7.78,
    0, '1h', '2026-03-08T18:36:22.479990'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3053,
    pnl_amount = -3.41,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FEC0C06A35ECAA69', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2023-11-23 13:00:00', '2023-11-23 20:19:21', 767.09477152, 763.69805837,
    778.6011931, 747.91740224, 0.1134,
    0.4428, 5.02, 'TRAILING_STOP', 7.32,
    1, '1h', '2026-03-08T18:36:22.477689'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4428,
    pnl_amount = 5.02,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C679F9CAFD20F463', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2023-11-24 03:00:00', '2023-11-24 05:38:14', 4693.26555452, 4723.09413426,
    4622.86657121, 4810.59719339, 0.1093,
    0.6356, 6.94, 'TIME_EXIT', 2.64,
    1, '1h', '2026-03-08T18:36:22.476909'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6356,
    pnl_amount = 6.94,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EEE9432B9D296FEC', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-11-24 09:00:00', '2023-11-24 18:08:29', 2241.53331393, 2251.89343523,
    2207.91031422, 2297.57164678, 0.0985,
    0.4622, 4.55, 'TRAILING_STOP', 9.14,
    1, '1h', '2026-03-08T18:36:22.479116'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4622,
    pnl_amount = 4.55,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BB143E920A0E4BD5', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2023-11-24 12:00:00', '2023-11-24 17:52:21', 3086.65317659, 3099.96660618,
    3040.35337894, 3163.819506, 0.0875,
    0.4313, 3.77, 'TAKE_PROFIT', 5.87,
    1, '1h', '2026-03-08T18:36:22.478945'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4313,
    pnl_amount = 3.77,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D62A9C1DB9FDDC5C', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2023-11-24 17:00:00', '2023-11-24 22:56:00', 4473.32817005, 4501.91465073,
    4406.22824749, 4585.1613743, 0.0876,
    0.639, 5.6, 'TIME_EXIT', 5.93,
    1, '1h', '2026-03-08T18:36:22.479294'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.639,
    pnl_amount = 5.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B75BC7C6CDCFDCF5', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2023-11-25 10:00:00', '2023-11-25 14:28:14', 14706.24458151, 14605.00841164,
    14926.83825023, 14338.58846697, 0.0955,
    0.6884, 6.57, 'TIME_EXIT', 4.47,
    1, '1h', '2026-03-08T18:36:22.483302'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6884,
    pnl_amount = 6.57,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B2B36ECC4A79365A', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2023-12-05 12:00:00', '2023-12-05 23:48:32', 1522.29535865, 1527.45440594,
    1545.12978903, 1484.23797468, 0.0861,
    -0.3389, -2.92, 'TIME_EXIT', 11.81,
    0, '1h', '2026-03-08T18:36:22.476948'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3389,
    pnl_amount = -2.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7CE1EB01333FEC3C', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-12-07 11:00:00', '2023-12-07 15:15:50', 35.07494178, 34.97860778,
    34.54881766, 35.95181533, 0.1162,
    -0.2747, -3.19, 'TIME_EXIT', 4.26,
    0, '1h', '2026-03-08T18:36:22.478530'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2747,
    pnl_amount = -3.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BFB964174D6B5EEC', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2023-12-09 02:00:00', '2023-12-09 12:42:58', 3714.87679699, 3733.18566083,
    3659.15364503, 3807.74871691, 0.0969,
    0.4929, 4.78, 'TRAILING_STOP', 10.72,
    1, '1h', '2026-03-08T18:36:22.476838'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4929,
    pnl_amount = 4.78,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '57A1EC63BA23DBD5', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2023-12-10 02:00:00', '2023-12-10 10:38:36', 152.74899937, 153.46684897,
    150.45776438, 156.56772435, 0.1028,
    0.47, 4.83, 'TIME_EXIT', 8.64,
    1, '1h', '2026-03-08T18:36:22.480695'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.47,
    pnl_amount = 4.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '07EDD4370FABF090', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2023-12-10 04:00:00', '2023-12-10 13:05:32', 3355.93846379, 3345.39599784,
    3305.59938683, 3439.83692538, 0.0895,
    -0.3141, -2.81, 'TIME_EXIT', 9.09,
    0, '1h', '2026-03-08T18:36:22.482967'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3141,
    pnl_amount = -2.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D5E634CB5E95E637', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2023-12-14 04:00:00', '2023-12-14 09:57:49', 2954.99460386, 2972.5258227,
    2910.66968481, 3028.86946896, 0.0953,
    0.5933, 5.65, 'TIME_EXIT', 5.96,
    1, '1h', '2026-03-08T18:36:22.480064'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5933,
    pnl_amount = 5.65,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '740616DC1A28252C', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2023-12-16 18:00:00', '2023-12-16 20:32:43', 4704.56695926, 4735.22489979,
    4633.99845487, 4822.18113324, 0.115,
    0.6517, 7.5, 'TIME_EXIT', 2.55,
    1, '1h', '2026-03-08T18:36:22.477130'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6517,
    pnl_amount = 7.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C5CDED5D2848EA4', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2023-12-18 14:00:00', '2023-12-18 19:39:07', 2565.00173152, 2556.73107054,
    2526.52670554, 2629.1267748, 0.0917,
    -0.3224, -2.96, 'TIME_EXIT', 5.65,
    0, '1h', '2026-03-08T18:36:22.482153'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3224,
    pnl_amount = -2.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6EBE20240379FBD4', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2023-12-21 13:00:00', '2023-12-21 20:30:11', 2114.72219508, 2128.54292903,
    2083.00136215, 2167.59024995, 0.1099,
    0.6535, 7.18, 'TAKE_PROFIT', 7.5,
    1, '1h', '2026-03-08T18:36:22.477195'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6535,
    pnl_amount = 7.18,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5C5E91AB66C8117C', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-12-22 21:00:00', '2023-12-23 04:59:13', 2013.907814, 2005.21775926,
    2044.11643121, 1963.56011865, 0.0836,
    0.4315, 3.61, 'TAKE_PROFIT', 7.99,
    1, '1h', '2026-03-08T18:36:22.475884'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4315,
    pnl_amount = 3.61,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B9B8BD0C609ED4C9', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2023-12-30 07:00:00', '2023-12-30 17:48:58', 3953.82740964, 3931.72053046,
    4013.13482079, 3854.9817244, 0.0966,
    0.5591, 5.4, 'TIME_EXIT', 10.82,
    1, '1h', '2026-03-08T18:36:22.476727'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5591,
    pnl_amount = 5.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '917E785616C59086', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2023-12-30 07:00:00', '2023-12-30 14:09:36', 4723.28711993, 4737.91450147,
    4794.13642673, 4605.20494193, 0.1094,
    -0.3097, -3.39, 'TIME_EXIT', 7.16,
    0, '1h', '2026-03-08T18:36:22.477858'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3097,
    pnl_amount = -3.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9FD358480EFF577D', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-01-03 00:00:00', '2024-01-03 03:41:47', 3010.97763356, 3000.63270773,
    2965.81296906, 3086.2520744, 0.1187,
    -0.3436, -4.08, 'TIME_EXIT', 3.7,
    0, '1h', '2026-03-08T18:36:22.483107'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3436,
    pnl_amount = -4.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8D93E86F0AC864CD', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-01-04 23:00:00', '2024-01-05 07:53:11', 4995.50769642, 5013.98934584,
    5070.44031187, 4870.62000401, 0.0999,
    -0.37, -3.7, 'STOP_LOSS', 8.89,
    0, '1h', '2026-03-08T18:36:22.482619'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.37,
    pnl_amount = -3.7,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10005CC22EF74C61', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-01-08 11:00:00', '2024-01-08 21:56:07', 2533.63393, 2518.67873587,
    2571.63843895, 2470.29308175, 0.0842,
    0.5903, 4.97, 'TIME_EXIT', 10.94,
    1, '1h', '2026-03-08T18:36:22.479230'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5903,
    pnl_amount = 4.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DE3A4F623B2D69FB', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2024-01-15 10:00:00', '2024-01-15 21:38:07', 4862.23119259, 4893.81915158,
    4789.2977247, 4983.78697241, 0.0806,
    0.6497, 5.24, 'TAKE_PROFIT', 11.64,
    1, '1h', '2026-03-08T18:36:22.477112'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6497,
    pnl_amount = 5.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B353F8B0F49BC127', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-01-16 00:00:00', '2024-01-16 07:42:05', 3761.98061182, 3782.29671901,
    3705.55090265, 3856.03012712, 0.1094,
    0.54, 5.91, 'TIME_EXIT', 7.7,
    1, '1h', '2026-03-08T18:36:22.478327'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.54,
    pnl_amount = 5.91,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9386AFD4BB6C4F00', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-01-22 09:00:00', '2024-01-22 11:46:49', 567.70387702, 564.93857259,
    576.21943517, 553.51128009, 0.1061,
    0.4871, 5.17, 'TRAILING_STOP', 2.78,
    1, '1h', '2026-03-08T18:36:22.482863'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4871,
    pnl_amount = 5.17,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA3B2DCE9B168EB4', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-01-24 01:00:00', '2024-01-24 07:17:17', 105.55725583, 105.13734552,
    107.14061466, 102.91832443, 0.1,
    0.3978, 3.98, 'TIME_EXIT', 6.29,
    1, '1h', '2026-03-08T18:36:22.482207'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3978,
    pnl_amount = 3.98,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8B0909C583A2ED2A', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-01-26 21:00:00', '2024-01-27 07:50:05', 33042.54740401, 32815.47820715,
    33538.18561507, 32216.48371891, 0.0812,
    0.6872, 5.58, 'TIME_EXIT', 10.83,
    1, '1h', '2026-03-08T18:36:22.480543'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6872,
    pnl_amount = 5.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5C4E27DA4DE65994', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-01-27 12:00:00', '2024-01-27 14:17:16', 4352.17224362, 4366.55567258,
    4417.45482727, 4243.36793753, 0.0882,
    -0.3305, -2.92, 'TIME_EXIT', 2.29,
    0, '1h', '2026-03-08T18:36:22.484030'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3305,
    pnl_amount = -2.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0EDF9A1316B151BC', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-01-27 23:00:00', '2024-01-28 07:23:35', 30796.98745909, 30895.22262116,
    31258.94227098, 30027.06277261, 0.1085,
    -0.319, -3.46, 'STOP_LOSS', 8.39,
    0, '1h', '2026-03-08T18:36:22.482883'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.319,
    pnl_amount = -3.46,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1916A26663200968', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2024-02-15 23:00:00', '2024-02-16 02:38:26', 2476.74699221, 2470.08613466,
    2439.59578733, 2538.66566702, 0.0993,
    -0.2689, -2.67, 'STOP_LOSS', 3.64,
    0, '1h', '2026-03-08T18:36:22.483188'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2689,
    pnl_amount = -2.67,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F9E05E12A11486D', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-02-16 14:00:00', '2024-02-16 17:39:16', 2509.20035953, 2518.27188389,
    2546.83836492, 2446.47035054, 0.0828,
    -0.3615, -3.0, 'STOP_LOSS', 3.65,
    0, '1h', '2026-03-08T18:36:22.476341'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3615,
    pnl_amount = -3.0,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '650A358E27BD702A', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2024-02-25 02:00:00', '2024-02-25 05:37:23', 289.39299621, 291.20724291,
    285.05210127, 296.62782111, 0.0828,
    0.6269, 5.19, 'TAKE_PROFIT', 3.62,
    1, '1h', '2026-03-08T18:36:22.481380'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6269,
    pnl_amount = 5.19,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '749BF1B0B4F28CE7', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2024-02-27 22:00:00', '2024-02-28 07:36:14', 4198.01174849, 4180.16007609,
    4260.98192471, 4093.06145477, 0.1101,
    0.4252, 4.68, 'TAKE_PROFIT', 9.6,
    1, '1h', '2026-03-08T18:36:22.479498'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4252,
    pnl_amount = 4.68,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '04068E2DCAF39354', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-02-28 14:00:00', '2024-02-28 19:13:24', 35375.28555838, 35144.01571151,
    35905.91484175, 34490.90341942, 0.0803,
    0.6538, 5.25, 'TRAILING_STOP', 5.22,
    1, '1h', '2026-03-08T18:36:22.483153'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6538,
    pnl_amount = 5.25,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '63F805EF5C247211', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-03-01 12:00:00', '2024-03-01 21:09:37', 2302.17716896, 2311.21478246,
    2267.64451143, 2359.73159819, 0.1039,
    0.3926, 4.08, 'TAKE_PROFIT', 9.16,
    1, '1h', '2026-03-08T18:36:22.479434'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3926,
    pnl_amount = 4.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '127822942563273E', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-03-04 16:00:00', '2024-03-04 23:05:21', 2854.81620017, 2864.9059673,
    2897.63844318, 2783.44579517, 0.1069,
    -0.3534, -3.78, 'STOP_LOSS', 7.09,
    0, '1h', '2026-03-08T18:36:22.482190'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3534,
    pnl_amount = -3.78,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D35DA1C119320CD9', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2024-03-05 14:00:00', '2024-03-05 16:04:44', 1966.24701214, 1953.45200972,
    1995.74071733, 1917.09083684, 0.1121,
    0.6507, 7.3, 'TRAILING_STOP', 2.08,
    1, '1h', '2026-03-08T18:36:22.483571'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6507,
    pnl_amount = 7.3,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F62BF1F5A8938DB5', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-03-07 17:00:00', '2024-03-08 04:58:09', 4680.55821645, 4710.84661089,
    4610.34984321, 4797.57217186, 0.0893,
    0.6471, 5.78, 'TIME_EXIT', 11.97,
    1, '1h', '2026-03-08T18:36:22.479415'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6471,
    pnl_amount = 5.78,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7FF9774BD46B5FF4', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2024-03-11 20:00:00', '2024-03-12 03:00:15', 4532.77134691, 4547.44485821,
    4600.76291711, 4419.45206324, 0.0865,
    -0.3237, -2.8, 'STOP_LOSS', 7.0,
    0, '1h', '2026-03-08T18:36:22.480479'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3237,
    pnl_amount = -2.8,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '618D298BDE8DDD9B', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-03-12 01:00:00', '2024-03-12 06:35:52', 3683.49895282, 3704.25295153,
    3628.24646853, 3775.58642664, 0.0894,
    0.5634, 5.04, 'TIME_EXIT', 5.6,
    1, '1h', '2026-03-08T18:36:22.481602'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5634,
    pnl_amount = 5.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B0187FE71DC4EB59', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-03-12 20:00:00', '2024-03-13 03:39:53', 40609.85526138, 40334.27938592,
    41219.0030903, 39594.60887984, 0.085,
    0.6786, 5.77, 'TIME_EXIT', 7.66,
    1, '1h', '2026-03-08T18:36:22.479212'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6786,
    pnl_amount = 5.77,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '81A43CD7A5680E0F', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-03-13 11:00:00', '2024-03-13 22:21:32', 4577.44153046, 4606.99705946,
    4508.77990751, 4691.87756873, 0.1138,
    0.6457, 7.35, 'TRAILING_STOP', 11.36,
    1, '1h', '2026-03-08T18:36:22.476451'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6457,
    pnl_amount = 7.35,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D4C5A231F7ADCD31', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-03-16 13:00:00', '2024-03-16 20:54:33', 783.35909612, 779.76570417,
    795.10948257, 763.77511872, 0.1168,
    0.4587, 5.36, 'TAKE_PROFIT', 7.91,
    1, '1h', '2026-03-08T18:36:22.477433'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4587,
    pnl_amount = 5.36,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A3022E45EACD7F95', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2024-03-16 13:00:00', '2024-03-16 21:48:49', 1475.16039212, 1479.85759615,
    1497.287798, 1438.28138232, 0.0861,
    -0.3184, -2.74, 'STOP_LOSS', 8.81,
    0, '1h', '2026-03-08T18:36:22.482106'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3184,
    pnl_amount = -2.74,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8FD23FCA6573498D', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-03-18 07:00:00', '2024-03-18 13:48:51', 182.64710392, 183.20753489,
    185.38681048, 178.08092633, 0.1177,
    -0.3068, -3.61, 'TIME_EXIT', 6.81,
    0, '1h', '2026-03-08T18:36:22.478412'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3068,
    pnl_amount = -3.61,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7ADCF50475007309', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-03-19 21:00:00', '2024-03-20 02:47:59', 2240.80242472, 2232.50441988,
    2207.19038835, 2296.82248534, 0.1147,
    -0.3703, -4.25, 'STOP_LOSS', 5.8,
    0, '1h', '2026-03-08T18:36:22.480352'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3703,
    pnl_amount = -4.25,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '31F4AFBB87C6446F', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-03-22 06:00:00', '2024-03-22 14:05:37', 1620.47242394, 1625.65864272,
    1644.7795103, 1579.96061334, 0.1135,
    -0.32, -3.63, 'STOP_LOSS', 8.09,
    0, '1h', '2026-03-08T18:36:22.480138'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.32,
    pnl_amount = -3.63,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1296D26FC4C279DD', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-03-24 07:00:00', '2024-03-24 13:23:17', 8248.85898725, 8200.57960821,
    8372.59187206, 8042.63751257, 0.0869,
    0.5853, 5.09, 'TAKE_PROFIT', 6.39,
    1, '1h', '2026-03-08T18:36:22.482846'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5853,
    pnl_amount = 5.09,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '82EC7BA0B40005DD', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-03-25 23:00:00', '2024-03-26 06:06:37', 15100.60892769, 15040.4014305,
    15327.1180616, 14723.0937045, 0.0996,
    0.3987, 3.97, 'TIME_EXIT', 7.11,
    1, '1h', '2026-03-08T18:36:22.481674'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3987,
    pnl_amount = 3.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2C070CFEB145E2D1', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-03-27 07:00:00', '2024-03-27 09:25:21', 36961.18211942, 37153.88536457,
    36406.76438762, 37885.2116724, 0.1175,
    0.5214, 6.13, 'TIME_EXIT', 2.42,
    1, '1h', '2026-03-08T18:36:22.476136'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5214,
    pnl_amount = 6.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '655E884F462D78AB', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-03-28 23:00:00', '2024-03-29 02:04:00', 2188.82241803, 2180.76260172,
    2221.6547543, 2134.10185758, 0.1194,
    0.3682, 4.4, 'TIME_EXIT', 3.07,
    1, '1h', '2026-03-08T18:36:22.478458'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3682,
    pnl_amount = 4.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B0047AE7C79462E6', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-04-01 19:00:00', '2024-04-01 23:22:42', 4668.3361292, 4643.95710379,
    4738.36117114, 4551.62772597, 0.1131,
    0.5222, 5.91, 'TRAILING_STOP', 4.38,
    1, '1h', '2026-03-08T18:36:22.478121'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5222,
    pnl_amount = 5.91,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BA2AD5F8DE4AE06F', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-04-02 12:00:00', '2024-04-02 18:03:24', 1117.89564504, 1123.87911892,
    1101.12721036, 1145.84303616, 0.1065,
    0.5352, 5.7, 'TIME_EXIT', 6.06,
    1, '1h', '2026-03-08T18:36:22.483430'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5352,
    pnl_amount = 5.7,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5862A77EEE6CC7EC', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-04-03 11:00:00', '2024-04-03 21:09:20', 2796.63849265, 2779.12496859,
    2838.58807004, 2726.72253033, 0.0949,
    0.6262, 5.94, 'TRAILING_STOP', 10.16,
    1, '1h', '2026-03-08T18:36:22.475780'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6262,
    pnl_amount = 5.94,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '01C28197820B520B', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2024-04-08 05:00:00', '2024-04-08 13:19:17', 3778.45364404, 3754.99485769,
    3835.1304487, 3683.99230294, 0.0839,
    0.6209, 5.21, 'TAKE_PROFIT', 8.32,
    1, '1h', '2026-03-08T18:36:22.480797'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6209,
    pnl_amount = 5.21,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '684DBE05FD63A14A', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2024-04-10 03:00:00', '2024-04-10 11:14:36', 4515.16510412, 4486.48923159,
    4582.89258068, 4402.28597651, 0.104,
    0.6351, 6.6, 'TIME_EXIT', 8.24,
    1, '1h', '2026-03-08T18:36:22.477139'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6351,
    pnl_amount = 6.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '95413FCBD8F2B1A6', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-04-11 04:00:00', '2024-04-11 10:17:39', 28517.83349221, 28365.15400702,
    28945.6009946, 27804.88765491, 0.0861,
    0.5354, 4.61, 'TAKE_PROFIT', 6.29,
    1, '1h', '2026-03-08T18:36:22.478606'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5354,
    pnl_amount = 4.61,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D067A739361B8857', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2024-04-11 14:00:00', '2024-04-11 23:30:18', 1920.76724401, 1928.12083198,
    1949.57875267, 1872.7480629, 0.1,
    -0.3828, -3.83, 'STOP_LOSS', 9.51,
    0, '1h', '2026-03-08T18:36:22.477406'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3828,
    pnl_amount = -3.83,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7DF0267445E885F6', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-04-12 03:00:00', '2024-04-12 06:59:48', 9755.1804605, 9704.08078558,
    9901.50816741, 9511.30094899, 0.0956,
    0.5238, 5.01, 'TRAILING_STOP', 4.0,
    1, '1h', '2026-03-08T18:36:22.478023'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5238,
    pnl_amount = 5.01,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8FBE4211F5DB44FA', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2024-04-12 03:00:00', '2024-04-12 13:26:01', 3855.66568753, 3868.8365705,
    3913.50067285, 3759.27404534, 0.1114,
    -0.3416, -3.81, 'TIME_EXIT', 10.43,
    0, '1h', '2026-03-08T18:36:22.481638'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3416,
    pnl_amount = -3.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C8FF8357106C1B08', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-04-14 06:00:00', '2024-04-14 13:04:20', 18797.51703739, 18868.91702968,
    18515.55428183, 19267.45496333, 0.0957,
    0.3798, 3.64, 'TRAILING_STOP', 7.07,
    1, '1h', '2026-03-08T18:36:22.479540'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3798,
    pnl_amount = 3.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DEA4A4535EA35802', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2024-04-14 07:00:00', '2024-04-14 11:58:50', 1192.99045212, 1188.00678737,
    1210.8853089, 1163.16569081, 0.1169,
    0.4177, 4.88, 'TAKE_PROFIT', 4.98,
    1, '1h', '2026-03-08T18:36:22.478212'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4177,
    pnl_amount = 4.88,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EDD86F324CF0B17B', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-04-23 14:00:00', '2024-04-24 01:48:20', 2772.49192577, 2782.56455151,
    2814.07930465, 2703.17962762, 0.0903,
    -0.3633, -3.28, 'STOP_LOSS', 11.81,
    0, '1h', '2026-03-08T18:36:22.483886'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3633,
    pnl_amount = -3.28,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9B1C0EFE56535D27', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2024-04-26 04:00:00', '2024-04-26 06:36:05', 4078.84525262, 4090.83932083,
    4140.02793141, 3976.87412131, 0.0988,
    -0.2941, -2.91, 'STOP_LOSS', 2.6,
    0, '1h', '2026-03-08T18:36:22.481931'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2941,
    pnl_amount = -2.91,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '019DAFEC071EECFF', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2024-04-26 16:00:00', '2024-04-26 20:32:53', 1195.63424567, 1190.9216416,
    1213.56875936, 1165.74338953, 0.0894,
    0.3942, 3.52, 'TIME_EXIT', 4.55,
    1, '1h', '2026-03-08T18:36:22.477497'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3942,
    pnl_amount = 3.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9DF8008C19B2718F', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2024-04-28 20:00:00', '2024-04-29 01:10:21', 4608.17456083, 4592.41783793,
    4539.05194242, 4723.37892485, 0.1151,
    -0.3419, -3.93, 'STOP_LOSS', 5.17,
    0, '1h', '2026-03-08T18:36:22.478726'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3419,
    pnl_amount = -3.93,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3F96C8DEBFB49F16', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-04-29 05:00:00', '2024-04-29 09:09:30', 1884.43394581, 1876.58179948,
    1912.700455, 1837.32309717, 0.1093,
    0.4167, 4.56, 'TIME_EXIT', 4.16,
    1, '1h', '2026-03-08T18:36:22.483787'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4167,
    pnl_amount = 4.56,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8B7D1BE23185BC55', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-04-30 08:00:00', '2024-04-30 13:06:03', 2074.54390391, 2083.56007802,
    2043.42574535, 2126.40750151, 0.0912,
    0.4346, 3.97, 'TAKE_PROFIT', 5.1,
    1, '1h', '2026-03-08T18:36:22.477839'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4346,
    pnl_amount = 3.97,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9D980DDBA4D689C8', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-04-30 16:00:00', '2024-05-01 02:52:38', 101.63815249, 102.0716314,
    100.1135802, 104.1791063, 0.1053,
    0.4265, 4.49, 'TIME_EXIT', 10.88,
    1, '1h', '2026-03-08T18:36:22.477320'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4265,
    pnl_amount = 4.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1F47142018B09EEE', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-05-01 11:00:00', '2024-05-01 22:08:03', 871.21561319, 865.97892193,
    884.28384739, 849.43522286, 0.0912,
    0.6011, 5.48, 'TRAILING_STOP', 11.13,
    1, '1h', '2026-03-08T18:36:22.482676'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6011,
    pnl_amount = 5.48,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8BA7B0EB6E1151E2', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-05-01 23:00:00', '2024-05-02 04:00:06', 33569.59305107, 33752.28750299,
    33066.04915531, 34408.83287735, 0.0946,
    0.5442, 5.15, 'TRAILING_STOP', 5.0,
    1, '1h', '2026-03-08T18:36:22.481175'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5442,
    pnl_amount = 5.15,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '71AE1A41CD96EE41', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-05-03 01:00:00', '2024-05-03 03:32:01', 47016.92986158, 47140.37985587,
    47722.1838095, 45841.50661504, 0.0878,
    -0.2626, -2.31, 'TIME_EXIT', 2.53,
    0, '1h', '2026-03-08T18:36:22.481166'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2626,
    pnl_amount = -2.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4DFAFA937FE6F5D1', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-05-06 02:00:00', '2024-05-06 12:45:18', 32816.62373887, 32636.56123077,
    33308.87309495, 31996.20814539, 0.0967,
    0.5487, 5.31, 'TIME_EXIT', 10.76,
    1, '1h', '2026-03-08T18:36:22.483504'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5487,
    pnl_amount = 5.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F6C622571DBC089', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-05-06 16:00:00', '2024-05-06 20:37:43', 1864.27411881, 1858.94009989,
    1836.31000703, 1910.88097178, 0.1168,
    -0.2861, -3.34, 'STOP_LOSS', 4.63,
    0, '1h', '2026-03-08T18:36:22.478857'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2861,
    pnl_amount = -3.34,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F36FB0E37ED1CF14', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2024-05-07 00:00:00', '2024-05-07 03:55:52', 3288.92161802, 3275.25880264,
    3338.25544229, 3206.69857757, 0.104,
    0.4154, 4.32, 'TIME_EXIT', 3.93,
    1, '1h', '2026-03-08T18:36:22.476900'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4154,
    pnl_amount = 4.32,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4AB84179512F3FCD', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-05-10 02:00:00', '2024-05-10 12:15:07', 2406.56540194, 2392.80031422,
    2442.66388297, 2346.4012669, 0.0803,
    0.572, 4.59, 'TIME_EXIT', 10.25,
    1, '1h', '2026-03-08T18:36:22.482819'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.572,
    pnl_amount = 4.59,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1E03DF9E1940CD4C', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2024-05-12 09:00:00', '2024-05-12 19:19:38', 1068.04911829, 1065.23639707,
    1052.02838151, 1094.75034625, 0.1062,
    -0.2634, -2.8, 'TIME_EXIT', 10.33,
    0, '1h', '2026-03-08T18:36:22.478557'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2634,
    pnl_amount = -2.8,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '20852B662F15B76D', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2024-05-12 17:00:00', '2024-05-13 00:18:20', 2069.46175288, 2055.94106533,
    2100.50367917, 2017.72520906, 0.1162,
    0.6533, 7.59, 'TRAILING_STOP', 7.31,
    1, '1h', '2026-03-08T18:36:22.476666'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6533,
    pnl_amount = 7.59,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F365E2637643565', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-05-14 14:00:00', '2024-05-15 00:40:25', 501.97374313, 499.97376106,
    509.50334928, 489.42439956, 0.1143,
    0.3984, 4.55, 'TRAILING_STOP', 10.67,
    1, '1h', '2026-03-08T18:36:22.477067'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3984,
    pnl_amount = 4.55,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '82D25F723DD4E288', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2024-05-19 01:00:00', '2024-05-19 05:32:49', 1923.36924817, 1933.81221406,
    1894.51870945, 1971.45347938, 0.1117,
    0.543, 6.06, 'TRAILING_STOP', 4.55,
    1, '1h', '2026-03-08T18:36:22.482438'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.543,
    pnl_amount = 6.06,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9D228075E994973C', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-05-19 22:00:00', '2024-05-20 00:33:27', 199.05758642, 200.34184622,
    196.07172263, 204.03402608, 0.1152,
    0.6452, 7.43, 'TAKE_PROFIT', 2.56,
    1, '1h', '2026-03-08T18:36:22.475767'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6452,
    pnl_amount = 7.43,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EE999E4BF37638EE', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2024-05-20 03:00:00', '2024-05-20 06:20:56', 748.21098809, 753.26151301,
    736.98782327, 766.91626279, 0.1063,
    0.675, 7.18, 'TIME_EXIT', 3.35,
    1, '1h', '2026-03-08T18:36:22.476107'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.675,
    pnl_amount = 7.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B8327773FC09E577', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-05-21 03:00:00', '2024-05-21 06:56:51', 2519.88367156, 2503.17391379,
    2557.68192663, 2456.88657977, 0.0894,
    0.6631, 5.93, 'TRAILING_STOP', 3.95,
    1, '1h', '2026-03-08T18:36:22.481583'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6631,
    pnl_amount = 5.93,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AEA8CB824F01D751', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-05-21 20:00:00', '2024-05-22 01:06:48', 19467.50639047, 19531.62197083,
    19759.51898632, 18980.81873071, 0.0909,
    -0.3293, -2.99, 'STOP_LOSS', 5.11,
    0, '1h', '2026-03-08T18:36:22.480110'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3293,
    pnl_amount = -2.99,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1502DA28792AD252', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2024-05-23 12:00:00', '2024-05-23 15:25:47', 2027.29948009, 2019.96865666,
    1996.88998789, 2077.98196709, 0.1086,
    -0.3616, -3.93, 'TIME_EXIT', 3.43,
    0, '1h', '2026-03-08T18:36:22.477442'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3616,
    pnl_amount = -3.93,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4AF73411FAAD6BAA', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-05-24 03:00:00', '2024-05-24 08:04:37', 3376.54251015, 3393.93717752,
    3325.8943725, 3460.95607291, 0.1155,
    0.5152, 5.95, 'TIME_EXIT', 5.08,
    1, '1h', '2026-03-08T18:36:22.481256'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5152,
    pnl_amount = 5.95,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DFD44C0424E7F520', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-06-02 14:00:00', '2024-06-02 19:47:02', 2562.5022386, 2572.85711863,
    2524.06470502, 2626.56479457, 0.099,
    0.4041, 4.0, 'TAKE_PROFIT', 5.78,
    1, '1h', '2026-03-08T18:36:22.482810'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4041,
    pnl_amount = 4.0,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '58677FF22F475E7D', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2024-06-04 23:00:00', '2024-06-05 06:18:22', 1244.70226605, 1253.22798421,
    1226.03173206, 1275.8198227, 0.1007,
    0.685, 6.9, 'TIME_EXIT', 7.31,
    1, '1h', '2026-03-08T18:36:22.481203'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.685,
    pnl_amount = 6.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5F4159D31BE30D16', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2024-06-07 16:00:00', '2024-06-08 02:35:23', 2822.42468912, 2832.5106225,
    2780.08831878, 2892.98530635, 0.0854,
    0.3573, 3.05, 'TRAILING_STOP', 10.59,
    1, '1h', '2026-03-08T18:36:22.479879'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3573,
    pnl_amount = 3.05,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E35D1EED7326CDD8', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2024-06-08 07:00:00', '2024-06-08 14:51:53', 2118.17939421, 2125.54520088,
    2149.95208512, 2065.22490935, 0.1,
    -0.3477, -3.48, 'TIME_EXIT', 7.86,
    0, '1h', '2026-03-08T18:36:22.475682'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3477,
    pnl_amount = -3.48,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '80C9F71AE1009E8D', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-06-09 04:00:00', '2024-06-09 11:44:11', 4253.87124733, 4228.66515878,
    4317.67931604, 4147.52446615, 0.103,
    0.5925, 6.11, 'TAKE_PROFIT', 7.74,
    1, '1h', '2026-03-08T18:36:22.482525'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5925,
    pnl_amount = 6.11,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CA97E37096F51D82', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-06-10 05:00:00', '2024-06-10 07:18:54', 34512.27215591, 34349.37898969,
    35029.95623825, 33649.46535201, 0.1109,
    0.472, 5.23, 'TIME_EXIT', 2.32,
    1, '1h', '2026-03-08T18:36:22.476164'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.472,
    pnl_amount = 5.23,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8874C5B818FC80C6', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2024-06-11 12:00:00', '2024-06-11 19:31:35', 2170.61144334, 2155.45586916,
    2203.17061499, 2116.34615725, 0.1044,
    0.6982, 7.29, 'TAKE_PROFIT', 7.53,
    1, '1h', '2026-03-08T18:36:22.483581'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6982,
    pnl_amount = 7.29,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9CFB4522F5A2092C', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2024-06-12 15:00:00', '2024-06-12 20:06:38', 4706.08122349, 4683.09569161,
    4776.67244184, 4588.4291929, 0.1027,
    0.4884, 5.02, 'TIME_EXIT', 5.11,
    1, '1h', '2026-03-08T18:36:22.482057'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4884,
    pnl_amount = 5.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D27E16A7908E1E8A', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-06-13 23:00:00', '2024-06-14 03:58:26', 3807.458836, 3784.6702111,
    3864.57071854, 3712.2723651, 0.1007,
    0.5985, 6.03, 'TAKE_PROFIT', 4.97,
    1, '1h', '2026-03-08T18:36:22.479027'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5985,
    pnl_amount = 6.03,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '15615B22DED455DB', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-06-15 22:00:00', '2024-06-16 01:19:37', 2739.21274588, 2726.11631467,
    2780.30093707, 2670.73242723, 0.1034,
    0.4781, 4.94, 'TAKE_PROFIT', 3.33,
    1, '1h', '2026-03-08T18:36:22.483864'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4781,
    pnl_amount = 4.94,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E0EB686CE7B30A6C', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2024-06-16 07:00:00', '2024-06-16 17:32:15', 2944.7169932, 2934.12542169,
    2988.8877481, 2871.09906837, 0.1029,
    0.3597, 3.7, 'TAKE_PROFIT', 10.54,
    1, '1h', '2026-03-08T18:36:22.477737'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3597,
    pnl_amount = 3.7,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A72E96516A983DC', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2024-06-18 05:00:00', '2024-06-18 14:47:52', 4971.24423342, 4985.2010557,
    5045.81289692, 4846.96312758, 0.0996,
    -0.2808, -2.79, 'TIME_EXIT', 9.8,
    0, '1h', '2026-03-08T18:36:22.482372'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2808,
    pnl_amount = -2.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '590D96C3B2B7176C', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-06-18 21:00:00', '2024-06-19 07:32:45', 3454.47982382, 3431.11994811,
    3506.29702118, 3368.11782822, 0.0849,
    0.6762, 5.74, 'TIME_EXIT', 10.55,
    1, '1h', '2026-03-08T18:36:22.481593'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6762,
    pnl_amount = 5.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EEE15CBB282785F0', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-06-21 12:00:00', '2024-06-21 17:34:04', 3531.02423201, 3514.49571862,
    3583.98959549, 3442.74862621, 0.082,
    0.4681, 3.84, 'TAKE_PROFIT', 5.57,
    1, '1h', '2026-03-08T18:36:22.476764'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4681,
    pnl_amount = 3.84,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '32F36A517403C1E3', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-06-22 04:00:00', '2024-06-22 14:40:26', 2411.20800929, 2419.98871339,
    2375.03988915, 2471.48820952, 0.1098,
    0.3642, 4.0, 'TRAILING_STOP', 10.67,
    1, '1h', '2026-03-08T18:36:22.481032'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3642,
    pnl_amount = 4.0,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '07FA8ABC3BE6DE11', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2024-06-23 11:00:00', '2024-06-23 16:11:34', 2604.1840376, 2611.16501244,
    2643.24679816, 2539.07943666, 0.0966,
    -0.2681, -2.59, 'STOP_LOSS', 5.19,
    0, '1h', '2026-03-08T18:36:22.478494'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2681,
    pnl_amount = -2.59,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5E3D487683029E2B', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-06-25 22:00:00', '2024-06-26 02:19:29', 10165.80116909, 10207.7129446,
    10013.31415156, 10419.94619832, 0.0921,
    0.4123, 3.8, 'TRAILING_STOP', 4.32,
    1, '1h', '2026-03-08T18:36:22.475845'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4123,
    pnl_amount = 3.8,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9A45666AE36EAFF7', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2024-06-25 23:00:00', '2024-06-26 01:32:50', 778.09042786, 776.08617161,
    766.41907144, 797.54268856, 0.0847,
    -0.2576, -2.18, 'STOP_LOSS', 2.55,
    0, '1h', '2026-03-08T18:36:22.484020'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2576,
    pnl_amount = -2.18,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F24E01E678260681', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-06-27 04:00:00', '2024-06-27 15:01:09', 3907.62356802, 3919.85639835,
    3966.23792154, 3809.93297882, 0.1067,
    -0.3131, -3.34, 'TIME_EXIT', 11.02,
    0, '1h', '2026-03-08T18:36:22.480977'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3131,
    pnl_amount = -3.34,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1E765701B3827534', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2024-06-27 11:00:00', '2024-06-27 22:17:12', 3741.88399076, 3719.67263345,
    3798.01225062, 3648.33689099, 0.1139,
    0.5936, 6.76, 'TIME_EXIT', 11.29,
    1, '1h', '2026-03-08T18:36:22.481971'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5936,
    pnl_amount = 6.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8CDDA146E58F2BE2', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2024-06-28 08:00:00', '2024-06-28 10:16:47', 3630.49087873, 3646.62424693,
    3576.03351555, 3721.2531507, 0.1161,
    0.4444, 5.16, 'TIME_EXIT', 2.28,
    1, '1h', '2026-03-08T18:36:22.477049'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4444,
    pnl_amount = 5.16,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2F313DEE0AEF25DD', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-07-03 06:00:00', '2024-07-03 17:54:16', 2795.35174365, 2786.12949075,
    2753.4214675, 2865.23553724, 0.0956,
    -0.3299, -3.15, 'TIME_EXIT', 11.9,
    0, '1h', '2026-03-08T18:36:22.477979'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3299,
    pnl_amount = -3.15,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F01352271307FBFE', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-07-03 23:00:00', '2024-07-04 06:26:04', 1430.77748931, 1422.59849945,
    1452.23915164, 1395.00805207, 0.0911,
    0.5716, 5.21, 'TRAILING_STOP', 7.43,
    1, '1h', '2026-03-08T18:36:22.481275'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5716,
    pnl_amount = 5.21,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A951E553B9648F9', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2024-07-04 03:00:00', '2024-07-04 10:58:03', 1033.62694932, 1036.57269698,
    1049.13135356, 1007.78627558, 0.1157,
    -0.285, -3.3, 'STOP_LOSS', 7.97,
    0, '1h', '2026-03-08T18:36:22.481841'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.285,
    pnl_amount = -3.3,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0FF53615549401A2', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-07-05 17:00:00', '2024-07-05 21:06:28', 93.43663529, 94.01796083,
    92.03508576, 95.77255117, 0.1081,
    0.6222, 6.73, 'TAKE_PROFIT', 4.11,
    1, '1h', '2026-03-08T18:36:22.481885'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6222,
    pnl_amount = 6.73,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '17E028FA80D11320', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2024-07-09 12:00:00', '2024-07-09 21:55:40', 4047.48970335, 4066.58855009,
    3986.7773578, 4148.67694593, 0.1115,
    0.4719, 5.26, 'TAKE_PROFIT', 9.93,
    1, '1h', '2026-03-08T18:36:22.482363'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4719,
    pnl_amount = 5.26,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4D453C3F8DA20E47', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-07-13 02:00:00', '2024-07-13 04:11:29', 2748.01698562, 2764.67732993,
    2706.79673083, 2816.71741026, 0.0856,
    0.6063, 5.19, 'TIME_EXIT', 2.19,
    1, '1h', '2026-03-08T18:36:22.480297'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6063,
    pnl_amount = 5.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1A710D0FB9EF301B', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-07-13 13:00:00', '2024-07-13 18:42:23', 4658.35156296, 4675.39971278,
    4588.47628951, 4774.81035203, 0.1035,
    0.366, 3.79, 'TAKE_PROFIT', 5.71,
    1, '1h', '2026-03-08T18:36:22.479710'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.366,
    pnl_amount = 3.79,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B29AF99766378881', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-07-15 17:00:00', '2024-07-16 00:39:56', 49902.27189164, 50132.88650769,
    49153.73781326, 51149.82868893, 0.0869,
    0.4621, 4.02, 'TIME_EXIT', 7.67,
    1, '1h', '2026-03-08T18:36:22.475874'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4621,
    pnl_amount = 4.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1EF7530BC02D87D5', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2024-07-17 15:00:00', '2024-07-17 18:04:29', 806.17339996, 809.92894895,
    794.08079896, 826.32773496, 0.1086,
    0.4658, 5.06, 'TRAILING_STOP', 3.07,
    1, '1h', '2026-03-08T18:36:22.479861'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4658,
    pnl_amount = 5.06,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9738B77C681E30C2', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-07-18 08:00:00', '2024-07-18 11:24:12', 855.68569709, 851.95117455,
    868.52098254, 834.29355466, 0.1047,
    0.4364, 4.57, 'TRAILING_STOP', 3.4,
    1, '1h', '2026-03-08T18:36:22.476049'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4364,
    pnl_amount = 4.57,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E2DBDB1EEDEBE293', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-07-18 09:00:00', '2024-07-18 12:47:10', 239.5392913, 238.81556821,
    235.94620193, 245.52777358, 0.1123,
    -0.3021, -3.39, 'STOP_LOSS', 3.79,
    0, '1h', '2026-03-08T18:36:22.479962'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3021,
    pnl_amount = -3.39,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0A2E9A2FE63FDF39', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-07-22 08:00:00', '2024-07-22 16:18:27', 33930.05465384, 34072.367538,
    33421.10383403, 34778.30602019, 0.1196,
    0.4194, 5.02, 'TRAILING_STOP', 8.31,
    1, '1h', '2026-03-08T18:36:22.478130'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4194,
    pnl_amount = 5.02,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0753C74BCFEB345A', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-07-22 19:00:00', '2024-07-23 04:34:07', 29423.46254717, 29525.62075607,
    29864.81448538, 28687.87598349, 0.108,
    -0.3472, -3.75, 'STOP_LOSS', 9.57,
    0, '1h', '2026-03-08T18:36:22.481786'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3472,
    pnl_amount = -3.75,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '600FF2CBC32CC06E', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-07-27 16:00:00', '2024-07-27 18:04:15', 3443.21423726, 3422.24897798,
    3494.86245082, 3357.13388133, 0.1196,
    0.6089, 7.28, 'TIME_EXIT', 2.07,
    1, '1h', '2026-03-08T18:36:22.481619'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6089,
    pnl_amount = 7.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E7CCC83D594A3DB3', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-07-28 14:00:00', '2024-07-28 17:22:52', 45611.18187139, 45399.46150519,
    46295.34959946, 44470.9023246, 0.1183,
    0.4642, 5.49, 'TAKE_PROFIT', 3.38,
    1, '1h', '2026-03-08T18:36:22.476716'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4642,
    pnl_amount = 5.49,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F768AC74C3F2227', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-08-02 18:00:00', '2024-08-03 02:20:49', 2904.085649, 2920.72590911,
    2860.52436426, 2976.68779022, 0.0886,
    0.573, 5.08, 'TAKE_PROFIT', 8.35,
    1, '1h', '2026-03-08T18:36:22.481656'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.573,
    pnl_amount = 5.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '445CE72FCDA3C036', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2024-08-03 21:00:00', '2024-08-04 07:13:25', 766.58166592, 770.38349956,
    755.08294093, 785.74620757, 0.114,
    0.4959, 5.65, 'TAKE_PROFIT', 10.22,
    1, '1h', '2026-03-08T18:36:22.482902'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4959,
    pnl_amount = 5.65,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D23C88B9D94AB145', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-08-05 10:00:00', '2024-08-05 12:25:42', 1240.32722462, 1247.29256434,
    1221.72231625, 1271.33540524, 0.1041,
    0.5616, 5.85, 'TIME_EXIT', 2.43,
    1, '1h', '2026-03-08T18:36:22.482261'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5616,
    pnl_amount = 5.85,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EC5CEF24EAB3106B', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-08-05 18:00:00', '2024-08-06 04:55:58', 35110.34887953, 34902.03318485,
    35637.00411273, 34232.59015755, 0.092,
    0.5933, 5.46, 'TRAILING_STOP', 10.93,
    1, '1h', '2026-03-08T18:36:22.481877'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5933,
    pnl_amount = 5.46,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '58E1D520EF14B1AA', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2024-08-07 21:00:00', '2024-08-07 23:29:31', 4159.61513792, 4173.90845915,
    4222.00936499, 4055.62475948, 0.0927,
    -0.3436, -3.19, 'TIME_EXIT', 2.49,
    0, '1h', '2026-03-08T18:36:22.483069'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3436,
    pnl_amount = -3.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '68347A1630C3586F', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2024-08-10 04:00:00', '2024-08-10 14:00:25', 922.50234037, 925.66549931,
    936.33987547, 899.43978186, 0.1047,
    -0.3429, -3.59, 'STOP_LOSS', 10.01,
    0, '1h', '2026-03-08T18:36:22.483162'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3429,
    pnl_amount = -3.59,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '340A2E376AC11060', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2024-08-10 16:00:00', '2024-08-10 21:12:33', 3227.52283601, 3216.20757532,
    3275.93567855, 3146.83476511, 0.1139,
    0.3506, 3.99, 'TRAILING_STOP', 5.21,
    1, '1h', '2026-03-08T18:36:22.479150'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3506,
    pnl_amount = 3.99,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D92D8F17B778C99E', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2024-08-11 13:00:00', '2024-08-12 00:48:09', 3957.45178907, 3935.84503409,
    4016.8135659, 3858.51549434, 0.0946,
    0.546, 5.16, 'TAKE_PROFIT', 11.8,
    1, '1h', '2026-03-08T18:36:22.476648'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.546,
    pnl_amount = 5.16,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C12E4503AA893181', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-08-21 20:00:00', '2024-08-21 23:18:20', 2905.17396486, 2919.52961928,
    2861.59635539, 2977.80331398, 0.1046,
    0.4941, 5.17, 'TIME_EXIT', 3.31,
    1, '1h', '2026-03-08T18:36:22.483421'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4941,
    pnl_amount = 5.17,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '004AD99C48F67DDF', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2024-08-23 09:00:00', '2024-08-23 17:58:20', 3998.89031084, 4012.50821984,
    4058.8736655, 3898.91805307, 0.1155,
    -0.3405, -3.93, 'STOP_LOSS', 8.97,
    0, '1h', '2026-03-08T18:36:22.475723'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3405,
    pnl_amount = -3.93,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CDDAAB6BF086EB38', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-08-25 08:00:00', '2024-08-25 10:53:24', 4335.83962577, 4314.54825882,
    4400.87722015, 4227.44363512, 0.0861,
    0.4911, 4.23, 'TAKE_PROFIT', 2.89,
    1, '1h', '2026-03-08T18:36:22.482234'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4911,
    pnl_amount = 4.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FB98E212D5AC5EFE', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-08-25 12:00:00', '2024-08-25 18:42:35', 141.77258971, 141.27413214,
    139.64600087, 145.31690446, 0.1121,
    -0.3516, -3.94, 'STOP_LOSS', 6.71,
    0, '1h', '2026-03-08T18:36:22.478588'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3516,
    pnl_amount = -3.94,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D2AB6E7E947D4826', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-09-05 11:00:00', '2024-09-05 13:36:47', 571.14461738, 575.08162134,
    562.57744812, 585.42323282, 0.1159,
    0.6893, 7.99, 'TIME_EXIT', 2.61,
    1, '1h', '2026-03-08T18:36:22.482720'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6893,
    pnl_amount = 7.99,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '25C11C53AFD6E435', 'VWAP_ELITE_v1', 'LTCUSDT', 'SHORT',
    '2024-09-06 13:00:00', '2024-09-06 23:23:10', 2738.47343785, 2748.96553195,
    2779.55053942, 2670.01160191, 0.1055,
    -0.3831, -4.04, 'TIME_EXIT', 10.39,
    0, '1h', '2026-03-08T18:36:22.476993'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3831,
    pnl_amount = -4.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '17E8AEE81DB95CD5', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2024-09-06 13:00:00', '2024-09-06 21:03:10', 11.14584714, 11.18766914,
    11.31303485, 10.86720096, 0.0952,
    -0.3752, -3.57, 'STOP_LOSS', 8.05,
    0, '1h', '2026-03-08T18:36:22.479567'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3752,
    pnl_amount = -3.57,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FA34F103E245C9EC', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2024-09-07 01:00:00', '2024-09-07 05:02:33', 2491.02433054, 2500.93617059,
    2453.65896558, 2553.2999388, 0.1123,
    0.3979, 4.47, 'TIME_EXIT', 4.04,
    1, '1h', '2026-03-08T18:36:22.482828'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3979,
    pnl_amount = 4.47,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '075A35388C4260F4', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-09-07 03:00:00', '2024-09-07 12:23:51', 49930.37597253, 50206.80954113,
    49181.42033294, 51178.63537184, 0.1131,
    0.5536, 6.26, 'TAKE_PROFIT', 9.4,
    1, '1h', '2026-03-08T18:36:22.482162'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5536,
    pnl_amount = 6.26,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '404C4780861A7B35', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-09-07 23:00:00', '2024-09-08 07:01:15', 411.3572686, 409.42402191,
    417.52762763, 401.07333689, 0.0862,
    0.47, 4.05, 'TRAILING_STOP', 8.02,
    1, '1h', '2026-03-08T18:36:22.483719'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.47,
    pnl_amount = 4.05,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '38B498621DCDD2C0', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-09-08 10:00:00', '2024-09-08 14:56:00', 3823.41223076, 3802.69233618,
    3880.76341422, 3727.82692499, 0.1186,
    0.5419, 6.43, 'TRAILING_STOP', 4.93,
    1, '1h', '2026-03-08T18:36:22.481102'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5419,
    pnl_amount = 6.43,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BFDA4C7891C44E1D', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-09-10 02:00:00', '2024-09-10 07:38:08', 4617.53460702, 4631.89391451,
    4686.79762613, 4502.09624185, 0.0874,
    -0.311, -2.72, 'STOP_LOSS', 5.64,
    0, '1h', '2026-03-08T18:36:22.479133'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.311,
    pnl_amount = -2.72,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '306C603D41453CA3', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-09-14 18:00:00', '2024-09-14 23:51:00', 913.7340477, 909.1061497,
    927.44005842, 890.89069651, 0.104,
    0.5065, 5.27, 'TIME_EXIT', 5.85,
    1, '1h', '2026-03-08T18:36:22.477524'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5065,
    pnl_amount = 5.27,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F1BE2A457EF77227', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2024-09-18 23:00:00', '2024-09-19 07:23:42', 2406.92442429, 2417.11388337,
    2370.82055792, 2467.0975349, 0.0907,
    0.4233, 3.84, 'TAKE_PROFIT', 8.4,
    1, '1h', '2026-03-08T18:36:22.481093'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4233,
    pnl_amount = 3.84,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '433337756728C3D6', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-09-19 20:00:00', '2024-09-20 02:40:44', 671.9895739, 674.67782637,
    661.9097303, 688.78931325, 0.1036,
    0.4, 4.15, 'TAKE_PROFIT', 6.68,
    1, '1h', '2026-03-08T18:36:22.481120'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4,
    pnl_amount = 4.15,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '74DA1E1812B4BA2C', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-09-25 03:00:00', '2024-09-25 12:54:06', 3146.11478283, 3127.76914795,
    3193.30650457, 3067.46191326, 0.1094,
    0.5831, 6.38, 'TAKE_PROFIT', 9.9,
    1, '1h', '2026-03-08T18:36:22.480552'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5831,
    pnl_amount = 6.38,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5D48080C65D8E0F5', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2024-09-26 17:00:00', '2024-09-26 23:24:04', 140.4113859, 141.19793878,
    138.30521511, 143.92167055, 0.091,
    0.5602, 5.1, 'TAKE_PROFIT', 6.4,
    1, '1h', '2026-03-08T18:36:22.482920'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5602,
    pnl_amount = 5.1,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4EBA5FA9C163C88D', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-09-29 01:00:00', '2024-09-29 08:17:59', 1692.95014147, 1701.71116043,
    1667.55588935, 1735.27389501, 0.0875,
    0.5175, 4.53, 'TAKE_PROFIT', 7.3,
    1, '1h', '2026-03-08T18:36:22.478203'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5175,
    pnl_amount = 4.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B373FAABEFCC17E7', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2024-09-29 12:00:00', '2024-09-29 14:16:47', 4848.87719674, 4870.4403837,
    4776.14403879, 4970.09912666, 0.0897,
    0.4447, 3.99, 'TIME_EXIT', 2.28,
    1, '1h', '2026-03-08T18:36:22.476098'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4447,
    pnl_amount = 3.99,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6E5FEF2DAAA3569D', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-10-02 05:00:00', '2024-10-02 07:39:19', 17665.39771745, 17550.69609762,
    17930.37868321, 17223.76277451, 0.116,
    0.6493, 7.53, 'TRAILING_STOP', 2.66,
    1, '1h', '2026-03-08T18:36:22.479638'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6493,
    pnl_amount = 7.53,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '84FE6C23783B61E0', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-10-03 21:00:00', '2024-10-04 07:49:18', 2205.45014399, 2219.89639378,
    2172.36839183, 2260.58639759, 0.0873,
    0.655, 5.72, 'TIME_EXIT', 10.82,
    1, '1h', '2026-03-08T18:36:22.479926'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.655,
    pnl_amount = 5.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B8372805E6AED888', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2024-10-07 13:00:00', '2024-10-07 15:17:09', 1832.09376281, 1825.7804693,
    1804.61235637, 1877.89610688, 0.11,
    -0.3446, -3.79, 'TIME_EXIT', 2.29,
    0, '1h', '2026-03-08T18:36:22.480506'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3446,
    pnl_amount = -3.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '985825A10EB17556', 'VWAP_ELITE_v1', 'DOTUSDT', 'LONG',
    '2024-10-08 07:00:00', '2024-10-08 18:56:48', 4262.53476387, 4287.00421003,
    4198.59674242, 4369.09813297, 0.1194,
    0.5741, 6.86, 'TIME_EXIT', 11.95,
    1, '1h', '2026-03-08T18:36:22.478744'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5741,
    pnl_amount = 6.86,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D3693B2167C7B20B', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-10-10 01:00:00', '2024-10-10 04:44:28', 2988.83749673, 3005.65477145,
    2944.00493428, 3063.55843415, 0.1003,
    0.5627, 5.64, 'TRAILING_STOP', 3.74,
    1, '1h', '2026-03-08T18:36:22.483403'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5627,
    pnl_amount = 5.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EAC05C2816D13338', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2024-10-10 21:00:00', '2024-10-11 06:50:30', 4396.39214886, 4380.37338941,
    4462.33803109, 4286.48234514, 0.08,
    0.3644, 2.92, 'TAKE_PROFIT', 9.84,
    1, '1h', '2026-03-08T18:36:22.481266'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3644,
    pnl_amount = 2.92,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F1EF160B1F4A5F5F', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-10-11 02:00:00', '2024-10-11 09:31:35', 36899.38851791, 37035.92000157,
    36345.89769014, 37821.87323086, 0.0811,
    0.37, 3.0, 'TIME_EXIT', 7.53,
    1, '1h', '2026-03-08T18:36:22.476040'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.37,
    pnl_amount = 3.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7B093E87A8F723EA', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2024-10-11 02:00:00', '2024-10-11 09:39:23', 3530.03826606, 3512.17761864,
    3582.98884005, 3441.78730941, 0.0866,
    0.506, 4.38, 'TAKE_PROFIT', 7.66,
    1, '1h', '2026-03-08T18:36:22.476231'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.506,
    pnl_amount = 4.38,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '47320383B0A4AC32', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2024-10-11 21:00:00', '2024-10-12 03:09:20', 2753.07321806, 2742.87615751,
    2794.36931633, 2684.2463876, 0.0977,
    0.3704, 3.62, 'TRAILING_STOP', 6.16,
    1, '1h', '2026-03-08T18:36:22.483447'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3704,
    pnl_amount = 3.62,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '19C1544FB63C8E48', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2024-10-16 17:00:00', '2024-10-16 21:17:47', 60.05378323, 59.89971695,
    59.15297648, 61.55512781, 0.1187,
    -0.2565, -3.04, 'TIME_EXIT', 4.3,
    0, '1h', '2026-03-08T18:36:22.483078'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2565,
    pnl_amount = -3.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '66E1FC8DEE331D44', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2024-10-17 09:00:00', '2024-10-17 17:54:06', 3672.8356774, 3652.76802063,
    3727.92821256, 3581.01478547, 0.112,
    0.5464, 6.12, 'TIME_EXIT', 8.9,
    1, '1h', '2026-03-08T18:36:22.480578'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5464,
    pnl_amount = 6.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A869451F5A855D2C', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2024-10-17 15:00:00', '2024-10-18 00:36:36', 1590.11947263, 1595.20726048,
    1613.97126472, 1550.36648581, 0.0845,
    -0.32, -2.7, 'TIME_EXIT', 9.61,
    0, '1h', '2026-03-08T18:36:22.478372'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.32,
    pnl_amount = -2.7,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '53B1850615C21072', 'VWAP_ELITE_v1', 'DOTUSDT', 'SHORT',
    '2024-10-19 15:00:00', '2024-10-20 02:56:45', 45.81947999, 45.59219347,
    46.50677219, 44.67399299, 0.0932,
    0.496, 4.62, 'TAKE_PROFIT', 11.95,
    1, '1h', '2026-03-08T18:36:22.476873'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.496,
    pnl_amount = 4.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2837A0F4C9C10FFF', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2024-10-20 12:00:00', '2024-10-20 22:03:49', 2742.50771712, 2758.26694913,
    2701.37010136, 2811.07041004, 0.0951,
    0.5746, 5.47, 'TAKE_PROFIT', 10.06,
    1, '1h', '2026-03-08T18:36:22.483835'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5746,
    pnl_amount = 5.47,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6DD3BC308F7DC8F1', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-10-20 20:00:00', '2024-10-21 02:25:02', 4905.07152039, 4884.59598973,
    4978.64759319, 4782.44473238, 0.0881,
    0.4174, 3.68, 'TAKE_PROFIT', 6.42,
    1, '1h', '2026-03-08T18:36:22.482216'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4174,
    pnl_amount = 3.68,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BAB1BA568E39AEBD', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2024-10-21 16:00:00', '2024-10-22 01:52:18', 1976.72259654, 1963.67232056,
    2006.37343549, 1927.30453162, 0.1046,
    0.6602, 6.9, 'TAKE_PROFIT', 9.87,
    1, '1h', '2026-03-08T18:36:22.481370'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6602,
    pnl_amount = 6.9,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA94DF1970346F8F', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2024-10-24 22:00:00', '2024-10-25 05:53:30', 1470.406172, 1465.21066227,
    1448.35007942, 1507.1663263, 0.0913,
    -0.3533, -3.22, 'TIME_EXIT', 7.89,
    0, '1h', '2026-03-08T18:36:22.483963'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3533,
    pnl_amount = -3.22,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ABA24E56E4DBBFFA', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-10-25 17:00:00', '2024-10-26 03:21:35', 1677.29686019, 1684.21817309,
    1652.13740729, 1719.22928169, 0.1092,
    0.4126, 4.51, 'TAKE_PROFIT', 10.36,
    1, '1h', '2026-03-08T18:36:22.482610'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4126,
    pnl_amount = 4.51,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DBCA2F6F5A796AED', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-10-26 06:00:00', '2024-10-26 15:58:07', 4607.39106747, 4637.95882378,
    4538.28020146, 4722.57584415, 0.117,
    0.6635, 7.76, 'TIME_EXIT', 9.97,
    1, '1h', '2026-03-08T18:36:22.483653'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6635,
    pnl_amount = 7.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BF5ACCA6341C5CA2', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-10-26 18:00:00', '2024-10-27 02:00:45', 4794.52718646, 4773.09143607,
    4866.44509426, 4674.6640068, 0.0926,
    0.4471, 4.14, 'TRAILING_STOP', 8.01,
    1, '1h', '2026-03-08T18:36:22.483746'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4471,
    pnl_amount = 4.14,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '188AB2B38BAB52E9', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-10-28 03:00:00', '2024-10-28 14:33:11', 3036.05809229, 3020.67696374,
    3081.59896367, 2960.15663998, 0.0845,
    0.5066, 4.28, 'TAKE_PROFIT', 11.55,
    1, '1h', '2026-03-08T18:36:22.482747'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5066,
    pnl_amount = 4.28,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75C200C34DCFEBF5', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-10-30 09:00:00', '2024-10-30 19:41:27', 3728.65202844, 3715.01742978,
    3672.72224801, 3821.86832915, 0.0954,
    -0.3657, -3.49, 'STOP_LOSS', 10.69,
    0, '1h', '2026-03-08T18:36:22.479832'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3657,
    pnl_amount = -3.49,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9EEE5D826221B1BE', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2024-10-31 07:00:00', '2024-10-31 14:18:10', 251.08097137, 249.63001441,
    254.84718594, 244.80394708, 0.0917,
    0.5779, 5.3, 'TRAILING_STOP', 7.3,
    1, '1h', '2026-03-08T18:36:22.479656'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5779,
    pnl_amount = 5.3,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '62F9068829CBD653', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2024-11-01 12:00:00', '2024-11-01 23:44:10', 1032.73043942, 1025.79918192,
    1048.22139602, 1006.91217844, 0.1026,
    0.6712, 6.88, 'TRAILING_STOP', 11.74,
    1, '1h', '2026-03-08T18:36:22.480343'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6712,
    pnl_amount = 6.88,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '587F105CD14E01F3', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-11-04 21:00:00', '2024-11-05 05:57:30', 4339.41323356, 4328.08380656,
    4274.32203505, 4447.8985644, 0.116,
    -0.2611, -3.03, 'TIME_EXIT', 8.96,
    0, '1h', '2026-03-08T18:36:22.476070'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2611,
    pnl_amount = -3.03,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '78632FE5F3E82E3A', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2024-11-08 18:00:00', '2024-11-09 04:55:52', 4786.31899203, 4805.14970285,
    4714.52420715, 4905.97696683, 0.119,
    0.3934, 4.68, 'TIME_EXIT', 10.93,
    1, '1h', '2026-03-08T18:36:22.481776'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3934,
    pnl_amount = 4.68,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '947C49CFA6DE6801', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2024-11-09 18:00:00', '2024-11-10 00:13:17', 1577.47060694, 1584.98800075,
    1553.80854784, 1616.90737212, 0.095,
    0.4765, 4.53, 'TAKE_PROFIT', 6.22,
    1, '1h', '2026-03-08T18:36:22.480270'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4765,
    pnl_amount = 4.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '15BC948A31DA17FE', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2024-11-09 18:00:00', '2024-11-10 01:11:24', 4463.0570193, 4450.35747634,
    4396.11116401, 4574.63344478, 0.1107,
    -0.2845, -3.15, 'TIME_EXIT', 7.19,
    0, '1h', '2026-03-08T18:36:22.481462'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2845,
    pnl_amount = -3.15,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '67D7CA7036AA8804', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-11-16 19:00:00', '2024-11-16 21:30:38', 7561.96774985, 7533.01173364,
    7675.39726609, 7372.9185561, 0.0913,
    0.3829, 3.5, 'TAKE_PROFIT', 2.51,
    1, '1h', '2026-03-08T18:36:22.482252'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3829,
    pnl_amount = 3.5,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC68160DC14CFB8C', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2024-11-16 23:00:00', '2024-11-17 05:47:22', 2189.03031339, 2182.6957671,
    2156.19485869, 2243.75607123, 0.1123,
    -0.2894, -3.25, 'STOP_LOSS', 6.79,
    0, '1h', '2026-03-08T18:36:22.477239'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2894,
    pnl_amount = -3.25,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B13B866661EE5EF5', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2024-11-19 17:00:00', '2024-11-19 19:16:26', 33210.46040566, 33078.51894615,
    33708.61731175, 32380.19889552, 0.0868,
    0.3973, 3.45, 'TAKE_PROFIT', 2.27,
    1, '1h', '2026-03-08T18:36:22.477012'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3973,
    pnl_amount = 3.45,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8FF5CE9A932370F3', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2024-11-21 12:00:00', '2024-11-21 17:40:58', 3471.77777312, 3485.4084788,
    3419.70110653, 3558.57221745, 0.0882,
    0.3926, 3.46, 'TAKE_PROFIT', 5.68,
    1, '1h', '2026-03-08T18:36:22.476200'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3926,
    pnl_amount = 3.46,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '429E0C832C53FCD2', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2024-12-01 02:00:00', '2024-12-01 09:26:31', 74.90242305, 75.27894775,
    73.77888671, 76.77498363, 0.1012,
    0.5027, 5.09, 'TIME_EXIT', 7.44,
    1, '1h', '2026-03-08T18:36:22.481574'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5027,
    pnl_amount = 5.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0F1464BAEEDA28D4', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2024-12-04 01:00:00', '2024-12-04 11:36:19', 1878.20526678, 1884.96691259,
    1906.37834578, 1831.25013511, 0.0827,
    -0.36, -2.98, 'STOP_LOSS', 10.61,
    0, '1h', '2026-03-08T18:36:22.482408'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.36,
    pnl_amount = -2.98,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '65BEAC3EC0C16E08', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2024-12-10 08:00:00', '2024-12-10 15:43:59', 4446.66637402, 4465.48126469,
    4379.96637841, 4557.83303337, 0.1113,
    0.4231, 4.71, 'TAKE_PROFIT', 7.73,
    1, '1h', '2026-03-08T18:36:22.480432'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4231,
    pnl_amount = 4.71,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0796D573E0E553E4', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2024-12-10 14:00:00', '2024-12-10 22:35:40', 23605.55994612, 23690.52568412,
    23251.47654693, 24195.69894477, 0.1095,
    0.3599, 3.94, 'TIME_EXIT', 8.59,
    1, '1h', '2026-03-08T18:36:22.478485'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3599,
    pnl_amount = 3.94,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '55DDCEDDA236FC3E', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2024-12-15 00:00:00', '2024-12-15 04:15:52', 4863.80426626, 4836.55858375,
    4936.76133025, 4742.2091596, 0.0808,
    0.5602, 4.52, 'TAKE_PROFIT', 4.26,
    1, '1h', '2026-03-08T18:36:22.475835'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5602,
    pnl_amount = 4.52,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4D9885EC06FD6B1B', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2024-12-16 18:00:00', '2024-12-16 20:05:51', 3759.03573277, 3785.03183587,
    3702.65019678, 3853.01162609, 0.1074,
    0.6916, 7.43, 'TIME_EXIT', 2.1,
    1, '1h', '2026-03-08T18:36:22.478032'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6916,
    pnl_amount = 7.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E00FDE03EFA1B6E3', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2024-12-19 19:00:00', '2024-12-19 21:34:03', 717.08426655, 713.68648767,
    727.84053054, 699.15715988, 0.1138,
    0.4738, 5.39, 'TRAILING_STOP', 2.57,
    1, '1h', '2026-03-08T18:36:22.480882'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4738,
    pnl_amount = 5.39,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '369E0FC78E62E25F', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2024-12-30 11:00:00', '2024-12-30 20:37:28', 4946.25036742, 4977.70265433,
    4872.05661191, 5069.9066266, 0.0997,
    0.6359, 6.34, 'TAKE_PROFIT', 9.62,
    1, '1h', '2026-03-08T18:36:22.481473'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6359,
    pnl_amount = 6.34,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8EB6F23580D5833B', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2024-12-31 05:00:00', '2024-12-31 09:27:32', 296.42892665, 295.11178529,
    300.87536055, 289.01820348, 0.0901,
    0.4443, 4.0, 'TIME_EXIT', 4.46,
    1, '1h', '2026-03-08T18:36:22.476058'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4443,
    pnl_amount = 4.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5FB45056999AB130', 'VWAP_ELITE_v1', 'XRPUSDT', 'LONG',
    '2025-01-02 06:00:00', '2025-01-02 08:05:58', 632.370024, 630.24005498,
    622.88447364, 648.1792746, 0.0989,
    -0.3368, -3.33, 'STOP_LOSS', 2.1,
    0, '1h', '2026-03-08T18:36:22.483465'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3368,
    pnl_amount = -3.33,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3B7AD0B1B0D08CD4', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2025-01-02 08:00:00', '2025-01-02 13:32:05', 949.0873965, 953.24289014,
    934.85108555, 972.81458141, 0.1176,
    0.4378, 5.15, 'TAKE_PROFIT', 5.53,
    1, '1h', '2026-03-08T18:36:22.482637'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4378,
    pnl_amount = 5.15,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E131382142EC7098', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2025-01-06 09:00:00', '2025-01-06 13:34:00', 3141.40070937, 3152.48160732,
    3094.27969873, 3219.93572711, 0.1155,
    0.3527, 4.07, 'TAKE_PROFIT', 4.57,
    1, '1h', '2026-03-08T18:36:22.483376'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3527,
    pnl_amount = 4.07,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6E4F13E7EFCF8C71', 'VWAP_ELITE_v1', 'ADAUSDT', 'SHORT',
    '2025-01-08 04:00:00', '2025-01-08 08:31:46', 364.88081668, 362.57940881,
    370.35402893, 355.75879627, 0.0889,
    0.6307, 5.61, 'TAKE_PROFIT', 4.53,
    1, '1h', '2026-03-08T18:36:22.483691'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6307,
    pnl_amount = 5.61,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ECF126BC834681C3', 'VWAP_ELITE_v1', 'LTCUSDT', 'LONG',
    '2025-01-10 02:00:00', '2025-01-10 10:30:21', 2079.77002498, 2071.85037318,
    2048.5734746, 2131.7642756, 0.117,
    -0.3808, -4.46, 'TIME_EXIT', 8.51,
    0, '1h', '2026-03-08T18:36:22.477776'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3808,
    pnl_amount = -4.46,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '24692ADDDC803245', 'VWAP_ELITE_v1', 'ETHUSDT', 'LONG',
    '2025-01-13 00:00:00', '2025-01-13 07:51:29', 3471.53643216, 3495.31877856,
    3419.46338568, 3558.32484297, 0.0834,
    0.6851, 5.71, 'TIME_EXIT', 7.86,
    1, '1h', '2026-03-08T18:36:22.483853'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6851,
    pnl_amount = 5.71,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F5FEFA5C669F5755', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2025-01-13 10:00:00', '2025-01-13 19:06:02', 3120.91263625, 3103.48798784,
    3167.72632579, 3042.88982034, 0.1144,
    0.5583, 6.39, 'TIME_EXIT', 9.1,
    1, '1h', '2026-03-08T18:36:22.477886'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5583,
    pnl_amount = 6.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BDB164475096F4D1', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2025-01-14 11:00:00', '2025-01-14 18:45:24', 2528.91303523, 2535.72882296,
    2566.84673076, 2465.69020935, 0.0887,
    -0.2695, -2.39, 'TIME_EXIT', 7.76,
    0, '1h', '2026-03-08T18:36:22.477285'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2695,
    pnl_amount = -2.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '28D539F153CBAE42', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2025-01-14 20:00:00', '2025-01-15 03:51:47', 1222.95999382, 1217.77001204,
    1241.30439373, 1192.38599398, 0.0943,
    0.4244, 4.0, 'TRAILING_STOP', 7.86,
    1, '1h', '2026-03-08T18:36:22.480650'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4244,
    pnl_amount = 4.0,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5723D7C951A9F99D', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2025-01-15 22:00:00', '2025-01-16 01:56:15', 2629.41541415, 2611.93169978,
    2668.85664536, 2563.6800288, 0.118,
    0.6649, 7.85, 'TAKE_PROFIT', 3.94,
    1, '1h', '2026-03-08T18:36:22.481157'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6649,
    pnl_amount = 7.85,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EBF0CC2856B4F9C3', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2025-01-18 00:00:00', '2025-01-18 11:46:54', 3792.11562827, 3774.64581499,
    3848.99736269, 3697.31273756, 0.1089,
    0.4607, 5.02, 'TIME_EXIT', 11.78,
    1, '1h', '2026-03-08T18:36:22.483662'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4607,
    pnl_amount = 5.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BE90A1433CB7C299', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2025-01-21 20:00:00', '2025-01-21 23:03:33', 2111.41963191, 2122.31884419,
    2079.74833743, 2164.20512271, 0.0969,
    0.5162, 5.0, 'TRAILING_STOP', 3.06,
    1, '1h', '2026-03-08T18:36:22.479603'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5162,
    pnl_amount = 5.0,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B1640F18B14F4247', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2025-01-23 18:00:00', '2025-01-24 01:46:55', 1975.08836518, 1985.61935421,
    1945.4620397, 2024.46557431, 0.0806,
    0.5332, 4.3, 'TAKE_PROFIT', 7.78,
    1, '1h', '2026-03-08T18:36:22.481859'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5332,
    pnl_amount = 4.3,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ADD82149B7BB500F', 'VWAP_ELITE_v1', 'BNBUSDT', 'LONG',
    '2025-01-23 23:00:00', '2025-01-24 08:59:21', 243.99874148, 244.8749203,
    240.33876036, 250.09871002, 0.091,
    0.3591, 3.27, 'TIME_EXIT', 9.99,
    1, '1h', '2026-03-08T18:36:22.482544'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3591,
    pnl_amount = 3.27,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '74CAF8423525E45C', 'VWAP_ELITE_v1', 'ETHUSDT', 'SHORT',
    '2025-01-27 03:00:00', '2025-01-27 05:00:33', 716.95422544, 713.86166908,
    727.70853882, 699.0303698, 0.0925,
    0.4313, 3.99, 'TRAILING_STOP', 2.01,
    1, '1h', '2026-03-08T18:36:22.480017'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4313,
    pnl_amount = 3.99,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '715FA34C0036B2BC', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2025-01-27 12:00:00', '2025-01-27 16:53:34', 1737.73125413, 1727.42140592,
    1763.79722294, 1694.28797278, 0.1193,
    0.5933, 7.08, 'TRAILING_STOP', 4.89,
    1, '1h', '2026-03-08T18:36:22.481448'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5933,
    pnl_amount = 7.08,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A15258AE0223EC22', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2025-01-27 18:00:00', '2025-01-28 04:59:11', 3659.87303265, 3646.83659964,
    3714.77112814, 3568.37620684, 0.0836,
    0.3562, 2.98, 'TRAILING_STOP', 10.99,
    1, '1h', '2026-03-08T18:36:22.477515'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3562,
    pnl_amount = 2.98,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '97995A83E10E348C', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2025-01-31 02:00:00', '2025-01-31 10:00:35', 257.53892145, 259.22680115,
    253.67583763, 263.97739449, 0.0855,
    0.6554, 5.6, 'TAKE_PROFIT', 8.01,
    1, '1h', '2026-03-08T18:36:22.479953'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6554,
    pnl_amount = 5.6,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A76C41CB0C22DEFC', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2025-02-02 13:00:00', '2025-02-02 16:01:16', 10033.39742425, 10069.80594085,
    10183.89838561, 9782.56248864, 0.1182,
    -0.3629, -4.29, 'STOP_LOSS', 3.02,
    0, '1h', '2026-03-08T18:36:22.478441'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3629,
    pnl_amount = -4.29,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '507DF542D419C0D6', 'VWAP_ELITE_v1', 'BTCUSDT', 'SHORT',
    '2025-02-03 11:00:00', '2025-02-03 22:21:52', 14792.14405909, 14720.16168181,
    15014.02621998, 14422.34045761, 0.1116,
    0.4866, 5.43, 'TIME_EXIT', 11.36,
    1, '1h', '2026-03-08T18:36:22.479470'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4866,
    pnl_amount = 5.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F0D24A79AE9956D3', 'VWAP_ELITE_v1', 'AVAXUSDT', 'LONG',
    '2025-02-06 17:00:00', '2025-02-06 20:48:19', 4311.70753913, 4339.99044096,
    4247.03192605, 4419.50022761, 0.0906,
    0.656, 5.95, 'TAKE_PROFIT', 3.81,
    1, '1h', '2026-03-08T18:36:22.476498'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.656,
    pnl_amount = 5.95,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1FF757FB6834BB73', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2025-02-11 02:00:00', '2025-02-11 06:52:37', 1990.26827308, 2003.45173533,
    1960.41424898, 2040.0249799, 0.094,
    0.6624, 6.23, 'TAKE_PROFIT', 4.88,
    1, '1h', '2026-03-08T18:36:22.479594'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6624,
    pnl_amount = 6.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7728F301040AF00D', 'VWAP_ELITE_v1', 'BTCUSDT', 'LONG',
    '2025-02-12 10:00:00', '2025-02-12 16:19:19', 43577.00658155, 43830.90086406,
    42923.35148282, 44666.43174609, 0.1093,
    0.5826, 6.37, 'TRAILING_STOP', 6.32,
    1, '1h', '2026-03-08T18:36:22.479268'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5826,
    pnl_amount = 6.37,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E9918E89E7EDC43D', 'VWAP_ELITE_v1', 'XRPUSDT', 'SHORT',
    '2025-02-13 18:00:00', '2025-02-14 00:10:58', 37.59756573, 37.37024152,
    38.16152922, 36.65762659, 0.0855,
    0.6046, 5.17, 'TRAILING_STOP', 6.18,
    1, '1h', '2026-03-08T18:36:22.477614'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6046,
    pnl_amount = 5.17,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '866D2F66815FE051', 'VWAP_ELITE_v1', 'LINKUSDT', 'LONG',
    '2025-02-17 14:00:00', '2025-02-17 17:51:37', 1838.45985989, 1831.4205734,
    1810.88296199, 1884.42135638, 0.0907,
    -0.3829, -3.47, 'TIME_EXIT', 3.86,
    0, '1h', '2026-03-08T18:36:22.477719'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3829,
    pnl_amount = -3.47,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2C8EB222B809CA93', 'VWAP_ELITE_v1', 'SOLUSDT', 'SHORT',
    '2025-02-23 15:00:00', '2025-02-24 01:48:20', 4999.33234334, 5015.12087013,
    5074.32232849, 4874.34903476, 0.1022,
    -0.3158, -3.23, 'TIME_EXIT', 10.81,
    0, '1h', '2026-03-08T18:36:22.478138'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3158,
    pnl_amount = -3.23,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7DDF3E591F98A548', 'VWAP_ELITE_v1', 'AVAXUSDT', 'SHORT',
    '2025-02-24 12:00:00', '2025-02-24 20:31:08', 2373.43470093, 2363.51774985,
    2409.03622144, 2314.0988334, 0.1069,
    0.4178, 4.47, 'TAKE_PROFIT', 8.52,
    1, '1h', '2026-03-08T18:36:22.476191'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4178,
    pnl_amount = 4.47,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0B0911483363CD7B', 'VWAP_ELITE_v1', 'SOLUSDT', 'LONG',
    '2025-02-26 07:00:00', '2025-02-26 13:25:46', 50.64573165, 50.48959563,
    49.88604568, 51.91187494, 0.0889,
    -0.3083, -2.74, 'TIME_EXIT', 6.43,
    0, '1h', '2026-03-08T18:36:22.483728'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3083,
    pnl_amount = -2.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '69796F62B59EE1E3', 'VWAP_ELITE_v1', 'ADAUSDT', 'LONG',
    '2025-02-26 12:00:00', '2025-02-26 14:15:24', 4251.06555253, 4266.06250618,
    4187.29956924, 4357.34219134, 0.1187,
    0.3528, 4.19, 'TRAILING_STOP', 2.26,
    1, '1h', '2026-03-08T18:36:22.477222'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3528,
    pnl_amount = 4.19,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD3A626EB034CF8C', 'VWAP_ELITE_v1', 'BNBUSDT', 'SHORT',
    '2025-02-27 10:00:00', '2025-02-27 18:00:39', 2341.84915609, 2332.25465202,
    2376.97689343, 2283.30292719, 0.0806,
    0.4097, 3.3, 'TIME_EXIT', 8.01,
    1, '1h', '2026-03-08T18:36:22.478450'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4097,
    pnl_amount = 3.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5C7BFB29C37C210C', 'VWAP_ELITE_v1', 'LINKUSDT', 'SHORT',
    '2025-02-27 16:00:00', '2025-02-27 19:53:48', 3966.31526337, 3950.13218199,
    4025.80999232, 3867.15738179, 0.1046,
    0.408, 4.27, 'TAKE_PROFIT', 3.9,
    1, '1h', '2026-03-08T18:36:22.477551'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.408,
    pnl_amount = 4.27,
    exit_reason = 'TAKE_PROFIT';