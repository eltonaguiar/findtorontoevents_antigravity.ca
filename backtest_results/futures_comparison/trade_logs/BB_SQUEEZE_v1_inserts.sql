-- Trade log for BB_SQUEEZE_v1
-- Generated: 2026-03-08T18:36:22.544225
-- Total trades: 678


INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1FA0DEBB5F375557', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2020-01-10 15:00:00', '2020-01-10 19:11:38', 2480.00970323, 2472.1977951,
    2442.80955768, 2542.00994581, 0.0959,
    -0.315, -3.02, 'STOP_LOSS', 4.19,
    0, '1h', '2026-03-08T18:36:22.521624'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.315,
    pnl_amount = -3.02,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '170497A0E3945F7D', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2020-01-11 07:00:00', '2020-01-11 12:51:26', 3993.16306111, 4012.98460874,
    3933.2656152, 4092.99213764, 0.0913,
    0.4964, 4.53, 'TIME_EXIT', 5.86,
    1, '1h', '2026-03-08T18:36:22.522891'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4964,
    pnl_amount = 4.53,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7EA46E5C20AFEFC5', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-01-11 16:00:00', '2020-01-12 00:43:03', 2435.15728308, 2425.01090294,
    2398.62992383, 2496.03621516, 0.0825,
    -0.4167, -3.44, 'TIME_EXIT', 8.72,
    0, '1h', '2026-03-08T18:36:22.520569'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4167,
    pnl_amount = -3.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DFCB5B99D66AAE65', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2020-01-13 17:00:00', '2020-01-13 19:23:37', 2562.65177373, 2549.74093512,
    2601.09155034, 2498.58547939, 0.0883,
    0.5038, 4.45, 'TAKE_PROFIT', 2.39,
    1, '1h', '2026-03-08T18:36:22.522972'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5038,
    pnl_amount = 4.45,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98FE06B30C8E8AC2', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2020-01-15 15:00:00', '2020-01-15 22:50:00', 1751.18181428, 1757.59894473,
    1777.44954149, 1707.40226892, 0.094,
    -0.3664, -3.44, 'TIME_EXIT', 7.83,
    0, '1h', '2026-03-08T18:36:22.518429'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3664,
    pnl_amount = -3.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3DFD121227A8EBB5', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-01-16 08:00:00', '2020-01-16 14:34:59', 42776.33268678, 42536.8686099,
    43417.97767708, 41706.92436961, 0.0806,
    0.5598, 4.51, 'TIME_EXIT', 6.58,
    1, '1h', '2026-03-08T18:36:22.519634'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5598,
    pnl_amount = 4.51,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B888931767FEF121', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2020-01-19 07:00:00', '2020-01-19 11:04:44', 2985.76756108, 2971.88891857,
    3030.55407449, 2911.12337205, 0.0918,
    0.4648, 4.27, 'TAKE_PROFIT', 4.08,
    1, '1h', '2026-03-08T18:36:22.519851'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4648,
    pnl_amount = 4.27,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CC56F2F8AF73F009', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-02-03 12:00:00', '2020-02-03 21:29:00', 34263.10491962, 34479.180845,
    33749.15834582, 35119.68254261, 0.0961,
    0.6306, 6.06, 'TAKE_PROFIT', 9.48,
    1, '1h', '2026-03-08T18:36:22.520551'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6306,
    pnl_amount = 6.06,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8351ADBE40B0F614', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-02-04 21:00:00', '2020-02-05 06:41:15', 38828.46523451, 38651.59706097,
    39410.89221303, 37857.75360365, 0.1109,
    0.4555, 5.05, 'TAKE_PROFIT', 9.69,
    1, '1h', '2026-03-08T18:36:22.520848'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4555,
    pnl_amount = 5.05,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5D154FDC6BACF3B5', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2020-02-11 10:00:00', '2020-02-11 13:34:32', 3901.68945731, 3886.62539572,
    3843.16411545, 3999.23169374, 0.1083,
    -0.3861, -4.18, 'STOP_LOSS', 3.58,
    0, '1h', '2026-03-08T18:36:22.518101'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3861,
    pnl_amount = -4.18,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98A0DF44BA12D1AD', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2020-02-15 01:00:00', '2020-02-15 10:48:11', 3111.81356788, 3134.08768533,
    3065.13636437, 3189.60890708, 0.1136,
    0.7158, 8.13, 'TIME_EXIT', 9.8,
    1, '1h', '2026-03-08T18:36:22.519123'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7158,
    pnl_amount = 8.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '434BA68B3A74CD02', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2020-02-18 21:00:00', '2020-02-19 01:45:01', 1714.03007214, 1706.93178262,
    1688.31962106, 1756.88082394, 0.0887,
    -0.4141, -3.67, 'TIME_EXIT', 4.75,
    0, '1h', '2026-03-08T18:36:22.520478'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4141,
    pnl_amount = -3.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C1C75C9E5C635D6', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2020-02-19 09:00:00', '2020-02-19 15:29:10', 145.51977042, 144.88259311,
    147.70256698, 141.88177616, 0.107,
    0.4379, 4.68, 'TRAILING_STOP', 6.49,
    1, '1h', '2026-03-08T18:36:22.522377'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4379,
    pnl_amount = 4.68,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8BC9B9B9A142F586', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2020-02-21 19:00:00', '2020-02-22 04:34:24', 2332.92598048, 2324.71195107,
    2297.93209077, 2391.24912999, 0.0962,
    -0.3521, -3.39, 'STOP_LOSS', 9.57,
    0, '1h', '2026-03-08T18:36:22.520280'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3521,
    pnl_amount = -3.39,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0AC3CEAD583C155B', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2020-02-24 05:00:00', '2020-02-24 15:49:59', 1392.52682361, 1396.51916906,
    1413.41472596, 1357.71365302, 0.0803,
    -0.2867, -2.3, 'TIME_EXIT', 10.83,
    0, '1h', '2026-03-08T18:36:22.518851'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2867,
    pnl_amount = -2.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C602C63F61E03E8F', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2020-02-24 11:00:00', '2020-02-24 21:54:20', 4605.41721029, 4576.19835594,
    4674.49846844, 4490.28178003, 0.0999,
    0.6344, 6.34, 'TAKE_PROFIT', 10.91,
    1, '1h', '2026-03-08T18:36:22.519160'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6344,
    pnl_amount = 6.34,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C4A1FF0AAAFE802F', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2020-02-26 07:00:00', '2020-02-26 18:13:53', 95.39078784, 94.73185395,
    96.82164966, 93.00601814, 0.1055,
    0.6908, 7.29, 'TRAILING_STOP', 11.23,
    1, '1h', '2026-03-08T18:36:22.523118'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6908,
    pnl_amount = 7.29,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '87820FB96349EEBA', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-02-29 17:00:00', '2020-03-01 01:20:01', 8296.08810408, 8329.71339397,
    8420.52942564, 8088.68590148, 0.105,
    -0.4053, -4.26, 'TIME_EXIT', 8.33,
    0, '1h', '2026-03-08T18:36:22.521085'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4053,
    pnl_amount = -4.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DFCF4BD45201EE11', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2020-03-02 03:00:00', '2020-03-02 06:16:29', 4905.50874847, 4925.89228497,
    4979.0913797, 4782.87102976, 0.114,
    -0.4155, -4.74, 'STOP_LOSS', 3.27,
    0, '1h', '2026-03-08T18:36:22.522407'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4155,
    pnl_amount = -4.74,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '94A37828D7873C51', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2020-03-02 21:00:00', '2020-03-03 02:58:57', 2928.00234093, 2944.67400177,
    2884.08230581, 3001.20239945, 0.1106,
    0.5694, 6.3, 'TAKE_PROFIT', 5.98,
    1, '1h', '2026-03-08T18:36:22.517708'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5694,
    pnl_amount = 6.3,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '25BB1B5B08D87F4E', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2020-03-03 20:00:00', '2020-03-04 05:02:04', 2907.68527915, 2898.16860508,
    2864.06999997, 2980.37741113, 0.0945,
    -0.3273, -3.09, 'STOP_LOSS', 9.03,
    0, '1h', '2026-03-08T18:36:22.518696'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3273,
    pnl_amount = -3.09,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C456CE25A031FB96', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-03-06 11:00:00', '2020-03-06 15:28:55', 4737.80275097, 4720.89760002,
    4666.73570971, 4856.24781975, 0.0966,
    -0.3568, -3.45, 'TIME_EXIT', 4.48,
    0, '1h', '2026-03-08T18:36:22.517436'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3568,
    pnl_amount = -3.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A8DAED1D77326D55', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2020-03-15 23:00:00', '2020-03-16 01:14:45', 4622.20151984, 4593.28692895,
    4691.53454264, 4506.64648185, 0.0849,
    0.6256, 5.31, 'TIME_EXIT', 2.25,
    1, '1h', '2026-03-08T18:36:22.519997'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6256,
    pnl_amount = 5.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C7221B0850314C38', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2020-03-26 04:00:00', '2020-03-26 12:21:54', 3275.34815131, 3292.64948074,
    3226.21792904, 3357.23185509, 0.1046,
    0.5282, 5.52, 'TRAILING_STOP', 8.37,
    1, '1h', '2026-03-08T18:36:22.521892'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5282,
    pnl_amount = 5.52,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EDD343CBC76A5640', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2020-03-30 08:00:00', '2020-03-30 10:46:19', 3449.92510455, 3435.74716751,
    3398.17622798, 3536.17323216, 0.0974,
    -0.411, -4.0, 'TIME_EXIT', 2.77,
    0, '1h', '2026-03-08T18:36:22.517546'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.411,
    pnl_amount = -4.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A3E0F04A78DAAF99', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2020-03-31 18:00:00', '2020-03-31 23:05:50', 4361.6436586, 4335.19694642,
    4427.06831348, 4252.60256714, 0.1196,
    0.6063, 7.25, 'TIME_EXIT', 5.1,
    1, '1h', '2026-03-08T18:36:22.523055'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6063,
    pnl_amount = 7.25,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8F3AB2D26B0D6FA1', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-04-04 13:00:00', '2020-04-04 15:23:18', 37388.71066545, 37244.7500627,
    36827.88000547, 38323.42843209, 0.0963,
    -0.385, -3.71, 'TIME_EXIT', 2.39,
    0, '1h', '2026-03-08T18:36:22.518981'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.385,
    pnl_amount = -3.71,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1F3F29FA465CECEC', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-04-05 07:00:00', '2020-04-05 12:34:49', 3683.08911849, 3669.61138206,
    3627.84278171, 3775.16634645, 0.0981,
    -0.3659, -3.59, 'TIME_EXIT', 5.58,
    0, '1h', '2026-03-08T18:36:22.523379'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3659,
    pnl_amount = -3.59,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1E127D7713CB596F', 'BB_SQUEEZE_v1', 'BNBUSDT', 'SHORT',
    '2020-04-05 10:00:00', '2020-04-05 14:19:37', 2105.44642478, 2094.05929055,
    2137.02812116, 2052.81026416, 0.1172,
    0.5408, 6.34, 'TAKE_PROFIT', 4.33,
    1, '1h', '2026-03-08T18:36:22.521817'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5408,
    pnl_amount = 6.34,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FFBCAF0CAC824B78', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2020-04-13 00:00:00', '2020-04-13 09:12:32', 3746.97972737, 3773.40632248,
    3690.77503146, 3840.65422055, 0.0829,
    0.7053, 5.85, 'TAKE_PROFIT', 9.21,
    1, '1h', '2026-03-08T18:36:22.520533'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7053,
    pnl_amount = 5.85,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0DB068032132EF73', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-04-14 15:00:00', '2020-04-14 17:55:56', 1483.64368613, 1489.92878829,
    1461.38903084, 1520.73477829, 0.0808,
    0.4236, 3.42, 'TAKE_PROFIT', 2.93,
    1, '1h', '2026-03-08T18:36:22.521273'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4236,
    pnl_amount = 3.42,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '44D2CAE412971D38', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2020-04-15 14:00:00', '2020-04-15 23:17:41', 4919.40730419, 4904.98365336,
    4845.61619462, 5042.39248679, 0.0841,
    -0.2932, -2.46, 'TIME_EXIT', 9.29,
    0, '1h', '2026-03-08T18:36:22.519969'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2932,
    pnl_amount = -2.46,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EB87C800B7DA0B8F', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2020-04-20 16:00:00', '2020-04-21 00:03:46', 823.78859252, 826.49312714,
    836.14542141, 803.19387771, 0.1187,
    -0.3283, -3.9, 'STOP_LOSS', 8.06,
    0, '1h', '2026-03-08T18:36:22.521705'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3283,
    pnl_amount = -3.9,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E7D5B049C83F1216', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2020-04-22 18:00:00', '2020-04-23 03:38:26', 1593.2277801, 1583.13398817,
    1617.1261968, 1553.3970856, 0.0837,
    0.6335, 5.3, 'TAKE_PROFIT', 9.64,
    1, '1h', '2026-03-08T18:36:22.521791'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6335,
    pnl_amount = 5.3,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '07AE49F24EDD3B3A', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-04-22 22:00:00', '2020-04-23 01:00:47', 49813.13288674, 50035.63688904,
    49065.93589344, 51058.46120891, 0.0822,
    0.4467, 3.67, 'TIME_EXIT', 3.01,
    1, '1h', '2026-03-08T18:36:22.520785'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4467,
    pnl_amount = 3.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '61C15492D0A656AF', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-04-28 07:00:00', '2020-04-28 17:58:09', 3888.5957393, 3915.19663291,
    3830.26680321, 3985.81063278, 0.0909,
    0.6841, 6.22, 'TAKE_PROFIT', 10.97,
    1, '1h', '2026-03-08T18:36:22.517169'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6841,
    pnl_amount = 6.22,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0A1E99EFBC24DF60', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2020-04-28 23:00:00', '2020-04-29 04:15:07', 4250.21308113, 4228.02002486,
    4313.96627734, 4143.9577541, 0.116,
    0.5222, 6.06, 'TIME_EXIT', 5.25,
    1, '1h', '2026-03-08T18:36:22.519758'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5222,
    pnl_amount = 6.06,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BDA2A88FFB0B342A', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2020-05-01 00:00:00', '2020-05-01 09:00:08', 1719.66116853, 1731.36512443,
    1693.866251, 1762.65269774, 0.0841,
    0.6806, 5.73, 'TIME_EXIT', 9.0,
    1, '1h', '2026-03-08T18:36:22.520928'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6806,
    pnl_amount = 5.73,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '95DBDBA0CB279D7A', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-05-04 18:00:00', '2020-05-05 03:20:09', 42986.84118189, 43126.17267116,
    43631.64379962, 41912.17015235, 0.0963,
    -0.3241, -3.12, 'TIME_EXIT', 9.34,
    0, '1h', '2026-03-08T18:36:22.521400'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3241,
    pnl_amount = -3.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '46D8D7D759D8209D', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-05-07 02:00:00', '2020-05-07 09:30:21', 15979.63290403, 15929.58942825,
    15739.93841047, 16379.12372664, 0.1073,
    -0.3132, -3.36, 'STOP_LOSS', 7.51,
    0, '1h', '2026-03-08T18:36:22.519803'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3132,
    pnl_amount = -3.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D6B51DF14A18CA34', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-05-07 08:00:00', '2020-05-07 18:41:45', 3470.8853097, 3495.97136265,
    3418.82203005, 3557.65744244, 0.1156,
    0.7228, 8.35, 'TIME_EXIT', 10.7,
    1, '1h', '2026-03-08T18:36:22.522810'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7228,
    pnl_amount = 8.35,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '42864608B8A10676', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2020-05-12 22:00:00', '2020-05-13 06:17:27', 1987.90381435, 1997.03209838,
    1958.08525713, 2037.60140971, 0.0953,
    0.4592, 4.38, 'TRAILING_STOP', 8.29,
    1, '1h', '2026-03-08T18:36:22.520437'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4592,
    pnl_amount = 4.38,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4BA10B2763A8A1C3', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-05-13 02:00:00', '2020-05-13 09:41:35', 33258.43037871, 33085.6888012,
    33757.30683439, 32426.96961924, 0.1174,
    0.5194, 6.1, 'TRAILING_STOP', 7.69,
    1, '1h', '2026-03-08T18:36:22.518206'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5194,
    pnl_amount = 6.1,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '95986124401E4BDD', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2020-05-14 16:00:00', '2020-05-14 18:40:45', 2231.15629189, 2223.48679807,
    2197.68894751, 2286.93519918, 0.0893,
    -0.3437, -3.07, 'STOP_LOSS', 2.68,
    0, '1h', '2026-03-08T18:36:22.519420'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3437,
    pnl_amount = -3.07,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DEF386A6B9CD0690', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2020-05-18 05:00:00', '2020-05-18 16:45:45', 4445.35960781, 4423.05752311,
    4512.04000193, 4334.22561762, 0.1082,
    0.5017, 5.43, 'TRAILING_STOP', 11.76,
    1, '1h', '2026-03-08T18:36:22.520232'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5017,
    pnl_amount = 5.43,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C88CDFC456B98A88', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2020-05-19 03:00:00', '2020-05-19 14:03:12', 433.20868061, 434.63485626,
    439.70681082, 422.37846359, 0.1136,
    -0.3292, -3.74, 'TIME_EXIT', 11.05,
    0, '1h', '2026-03-08T18:36:22.517242'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3292,
    pnl_amount = -3.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E79643DF1CF82453', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-05-22 05:00:00', '2020-05-22 10:47:09', 4781.99846389, 4803.46415048,
    4710.26848693, 4901.54842549, 0.0844,
    0.4489, 3.79, 'TRAILING_STOP', 5.79,
    1, '1h', '2026-03-08T18:36:22.518326'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4489,
    pnl_amount = 3.79,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F1F56493B5C88C06', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-05-23 14:00:00', '2020-05-24 00:46:59', 630.03884726, 633.86299078,
    620.58826455, 645.78981844, 0.0886,
    0.607, 5.38, 'TAKE_PROFIT', 10.78,
    1, '1h', '2026-03-08T18:36:22.522416'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.607,
    pnl_amount = 5.38,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6E6D748A4B952267', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-05-28 21:00:00', '2020-05-29 02:52:26', 35351.58234521, 35217.52081737,
    34821.30861003, 36235.37190384, 0.0957,
    -0.3792, -3.63, 'TIME_EXIT', 5.87,
    0, '1h', '2026-03-08T18:36:22.523302'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3792,
    pnl_amount = -3.63,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A791FF39421EBC22', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2020-06-04 15:00:00', '2020-06-04 17:32:20', 2957.39049112, 2971.59503445,
    2913.02963375, 3031.3252534, 0.0971,
    0.4803, 4.66, 'TRAILING_STOP', 2.54,
    1, '1h', '2026-03-08T18:36:22.519533'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4803,
    pnl_amount = 4.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F77FA407415201F8', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-06-07 11:00:00', '2020-06-07 14:35:53', 2645.42901341, 2660.42239156,
    2605.74757821, 2711.56473875, 0.0873,
    0.5668, 4.95, 'TAKE_PROFIT', 3.6,
    1, '1h', '2026-03-08T18:36:22.521039'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5668,
    pnl_amount = 4.95,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0A6C6F02ADD7F76E', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-06-08 20:00:00', '2020-06-08 23:14:23', 2286.93577957, 2298.98405122,
    2252.63174287, 2344.10917406, 0.1011,
    0.5268, 5.32, 'TRAILING_STOP', 3.24,
    1, '1h', '2026-03-08T18:36:22.521122'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5268,
    pnl_amount = 5.32,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C2B77FE1481AD495', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-06-10 13:00:00', '2020-06-10 17:54:52', 12034.93280744, 11961.28319413,
    12215.45679955, 11734.05948725, 0.1026,
    0.612, 6.28, 'TRAILING_STOP', 4.91,
    1, '1h', '2026-03-08T18:36:22.517445'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.612,
    pnl_amount = 6.28,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '73375E54363D292F', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-06-14 04:00:00', '2020-06-14 14:31:08', 4326.87335482, 4312.69085575,
    4261.97025449, 4435.04518869, 0.085,
    -0.3278, -2.79, 'TIME_EXIT', 10.52,
    0, '1h', '2026-03-08T18:36:22.519114'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3278,
    pnl_amount = -2.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '94CEC60806454080', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2020-06-14 21:00:00', '2020-06-15 04:20:37', 3063.39518324, 3041.26782982,
    3109.34611099, 2986.81030366, 0.0815,
    0.7223, 5.89, 'TRAILING_STOP', 7.34,
    1, '1h', '2026-03-08T18:36:22.517681'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7223,
    pnl_amount = 5.89,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BB68FD243AD6A1F3', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2020-06-19 02:00:00', '2020-06-19 04:14:45', 3651.93015979, 3636.99556637,
    3706.70911218, 3560.63190579, 0.1032,
    0.409, 4.22, 'TAKE_PROFIT', 2.25,
    1, '1h', '2026-03-08T18:36:22.517408'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.409,
    pnl_amount = 4.22,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C16DCC59A3661DE2', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-06-23 11:00:00', '2020-06-23 15:56:51', 605.62007533, 603.49339913,
    596.5357742, 620.76057721, 0.1186,
    -0.3512, -4.16, 'TIME_EXIT', 4.95,
    0, '1h', '2026-03-08T18:36:22.518771'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3512,
    pnl_amount = -4.16,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C19F5C4E2397583E', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2020-06-23 17:00:00', '2020-06-24 04:52:43', 1650.71130707, 1645.08049753,
    1625.95063747, 1691.97908975, 0.1199,
    -0.3411, -4.09, 'TIME_EXIT', 11.88,
    0, '1h', '2026-03-08T18:36:22.521651'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3411,
    pnl_amount = -4.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1CAA1B7B9FB5F4EF', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2020-06-26 15:00:00', '2020-06-26 21:04:59', 361.51051452, 359.81756112,
    366.93317224, 352.47275166, 0.1077,
    0.4683, 5.04, 'TAKE_PROFIT', 6.08,
    1, '1h', '2026-03-08T18:36:22.522010'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4683,
    pnl_amount = 5.04,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DF515BFA8E908B84', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2020-06-30 02:00:00', '2020-06-30 13:18:11', 4436.8384171, 4454.44949536,
    4503.39099335, 4325.91745667, 0.0825,
    -0.3969, -3.27, 'TIME_EXIT', 11.3,
    0, '1h', '2026-03-08T18:36:22.522168'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3969,
    pnl_amount = -3.27,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '79E26C7B9E6541B8', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2020-06-30 11:00:00', '2020-06-30 19:08:34', 2048.90946769, 2060.65936729,
    2018.17582567, 2100.13220438, 0.1122,
    0.5735, 6.44, 'TIME_EXIT', 8.14,
    1, '1h', '2026-03-08T18:36:22.519411'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5735,
    pnl_amount = 6.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '302E6EF7A43171F5', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2020-07-01 18:00:00', '2020-07-01 23:26:47', 658.87514017, 661.48078249,
    668.75826728, 642.40326167, 0.0837,
    -0.3955, -3.31, 'TIME_EXIT', 5.45,
    0, '1h', '2026-03-08T18:36:22.520609'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3955,
    pnl_amount = -3.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '52033D0B25F0B2B8', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2020-07-03 08:00:00', '2020-07-03 10:46:35', 2583.10132531, 2574.76458691,
    2544.35480543, 2647.67885844, 0.0801,
    -0.3227, -2.58, 'TIME_EXIT', 2.78,
    0, '1h', '2026-03-08T18:36:22.520466'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3227,
    pnl_amount = -2.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C3BC70D7A3261DFC', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2020-07-03 19:00:00', '2020-07-04 04:35:19', 1027.6523191, 1023.88974272,
    1012.23753431, 1053.34362707, 0.1075,
    -0.3661, -3.94, 'TIME_EXIT', 9.59,
    0, '1h', '2026-03-08T18:36:22.523284'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3661,
    pnl_amount = -3.94,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '575C9F663754A610', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-07-04 10:00:00', '2020-07-04 18:53:35', 43691.76686379, 43955.95405457,
    43036.39036083, 44784.06103539, 0.0869,
    0.6047, 5.25, 'TRAILING_STOP', 8.89,
    1, '1h', '2026-03-08T18:36:22.522461'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6047,
    pnl_amount = 5.25,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F3181D0134B2A5A5', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-07-06 09:00:00', '2020-07-06 17:22:19', 35263.84666448, 35401.53128676,
    34734.88896451, 36145.44283109, 0.1103,
    0.3904, 4.31, 'TAKE_PROFIT', 8.37,
    1, '1h', '2026-03-08T18:36:22.518299'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3904,
    pnl_amount = 4.31,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7D5FEA41776329E0', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-07-12 06:00:00', '2020-07-12 08:43:47', 3427.13969184, 3446.35854397,
    3375.73259647, 3512.81818414, 0.0978,
    0.5608, 5.48, 'TIME_EXIT', 2.73,
    1, '1h', '2026-03-08T18:36:22.520194'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5608,
    pnl_amount = 5.48,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A30F919A6B6F3D84', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2020-07-15 03:00:00', '2020-07-15 06:44:54', 364.14074504, 365.25982687,
    369.60285622, 355.03722642, 0.0828,
    -0.3073, -2.55, 'STOP_LOSS', 3.75,
    0, '1h', '2026-03-08T18:36:22.518797'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3073,
    pnl_amount = -2.55,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D1DE3BEF1C67B999', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2020-07-15 13:00:00', '2020-07-15 19:24:19', 2211.93290522, 2197.52721171,
    2245.1118988, 2156.63458259, 0.1163,
    0.6513, 7.57, 'TAKE_PROFIT', 6.41,
    1, '1h', '2026-03-08T18:36:22.517211'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6513,
    pnl_amount = 7.57,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B88A15905388FF44', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2020-07-17 10:00:00', '2020-07-17 12:01:52', 91.34187769, 92.02123687,
    89.97174953, 93.62542463, 0.0998,
    0.7438, 7.42, 'TRAILING_STOP', 2.03,
    1, '1h', '2026-03-08T18:36:22.518056'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7438,
    pnl_amount = 7.42,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D6DC11F37A4F01BD', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2020-07-20 11:00:00', '2020-07-20 16:54:35', 3451.35975483, 3463.0474754,
    3503.13015115, 3365.07576096, 0.1121,
    -0.3386, -3.79, 'STOP_LOSS', 5.91,
    0, '1h', '2026-03-08T18:36:22.520542'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3386,
    pnl_amount = -3.79,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6BFF544AEF8CD98B', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2020-07-26 12:00:00', '2020-07-26 15:31:20', 4385.04165872, 4410.03786791,
    4319.26603384, 4494.66770019, 0.0952,
    0.57, 5.43, 'TIME_EXIT', 3.52,
    1, '1h', '2026-03-08T18:36:22.519524'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.57,
    pnl_amount = 5.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D3710E40227A3824', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2020-08-04 21:00:00', '2020-08-05 07:10:00', 4705.5640125, 4683.3904981,
    4776.14747269, 4587.92491219, 0.0901,
    0.4712, 4.25, 'TRAILING_STOP', 10.17,
    1, '1h', '2026-03-08T18:36:22.517537'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4712,
    pnl_amount = 4.25,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7928CF486D6E04C4', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2020-08-11 03:00:00', '2020-08-11 09:37:14', 269.55800081, 271.57328222,
    265.5146308, 276.29695083, 0.0857,
    0.7476, 6.41, 'TRAILING_STOP', 6.62,
    1, '1h', '2026-03-08T18:36:22.517601'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7476,
    pnl_amount = 6.41,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C89EB9BCD622B0D6', 'BB_SQUEEZE_v1', 'BNBUSDT', 'SHORT',
    '2020-08-12 22:00:00', '2020-08-13 02:39:09', 2187.03855264, 2195.0618729,
    2219.84413093, 2132.36258882, 0.1144,
    -0.3669, -4.2, 'TIME_EXIT', 4.65,
    0, '1h', '2026-03-08T18:36:22.521981'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3669,
    pnl_amount = -4.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A88A5E3B033B4035', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-08-15 04:00:00', '2020-08-15 11:15:54', 2725.0815869, 2742.86864426,
    2684.2053631, 2793.20862657, 0.1038,
    0.6527, 6.78, 'TAKE_PROFIT', 7.27,
    1, '1h', '2026-03-08T18:36:22.520382'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6527,
    pnl_amount = 6.78,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FC4F7F4EE60BB0FC', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2020-08-17 10:00:00', '2020-08-17 18:47:49', 1033.49007094, 1037.30667083,
    1048.992422, 1007.65281916, 0.1075,
    -0.3693, -3.97, 'STOP_LOSS', 8.8,
    0, '1h', '2026-03-08T18:36:22.523167'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3693,
    pnl_amount = -3.97,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4BB794D4445DED87', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-08-21 17:00:00', '2020-08-21 23:23:00', 5544.69072764, 5503.3895139,
    5627.86108855, 5406.07345945, 0.0992,
    0.7449, 7.39, 'TIME_EXIT', 6.38,
    1, '1h', '2026-03-08T18:36:22.522946'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7449,
    pnl_amount = 7.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D1F39E1BC563AA37', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-08-22 17:00:00', '2020-08-23 02:57:53', 25025.9797926, 25131.09892456,
    24650.59009571, 25651.62928742, 0.1057,
    0.42, 4.44, 'TRAILING_STOP', 9.96,
    1, '1h', '2026-03-08T18:36:22.518687'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.42,
    pnl_amount = 4.44,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6C7078B6D3C5364D', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2020-08-25 10:00:00', '2020-08-25 13:28:41', 1899.81559207, 1906.70702525,
    1928.31282595, 1852.32020227, 0.0916,
    -0.3627, -3.32, 'STOP_LOSS', 3.48,
    0, '1h', '2026-03-08T18:36:22.519365'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3627,
    pnl_amount = -3.32,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '54B8F399712E69B9', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-08-28 08:00:00', '2020-08-28 11:15:17', 130.82264482, 130.4400365,
    128.86030515, 134.09321094, 0.1054,
    -0.2925, -3.08, 'TIME_EXIT', 3.25,
    0, '1h', '2026-03-08T18:36:22.518806'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2925,
    pnl_amount = -3.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '73DF23751FF93193', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-08-31 15:00:00', '2020-09-01 01:02:25', 34992.7028863, 34754.74935432,
    35517.59342959, 34117.88531414, 0.0828,
    0.68, 5.63, 'TIME_EXIT', 10.04,
    1, '1h', '2026-03-08T18:36:22.519441'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.68,
    pnl_amount = 5.63,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2B43DEEFB1B66A48', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2020-09-01 06:00:00', '2020-09-01 08:36:07', 4870.16582155, 4889.46800602,
    4797.11333423, 4991.91996709, 0.0817,
    0.3963, 3.24, 'TIME_EXIT', 2.6,
    1, '1h', '2026-03-08T18:36:22.520410'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3963,
    pnl_amount = 3.24,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7FB4A298E4D092C5', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-09-09 10:00:00', '2020-09-09 17:57:33', 6391.11058926, 6368.7376097,
    6295.24393042, 6550.88835399, 0.1054,
    -0.3501, -3.69, 'STOP_LOSS', 7.96,
    0, '1h', '2026-03-08T18:36:22.518945'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3501,
    pnl_amount = -3.69,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5426210C532D2512', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-09-14 22:00:00', '2020-09-15 06:57:17', 34801.87996095, 34569.91258415,
    35323.90816037, 33931.83296193, 0.0886,
    0.6665, 5.91, 'TRAILING_STOP', 8.95,
    1, '1h', '2026-03-08T18:36:22.520515'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6665,
    pnl_amount = 5.91,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '444167A7A12B8851', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2020-09-24 07:00:00', '2020-09-24 12:30:45', 2314.3969406, 2301.75838801,
    2349.11289471, 2256.53701709, 0.1106,
    0.5461, 6.04, 'TAKE_PROFIT', 5.51,
    1, '1h', '2026-03-08T18:36:22.521773'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5461,
    pnl_amount = 6.04,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3B0A2983939E77EA', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2020-10-04 03:00:00', '2020-10-04 11:10:12', 1476.62557014, 1472.2664073,
    1454.47618659, 1513.54120939, 0.0929,
    -0.2952, -2.74, 'STOP_LOSS', 8.17,
    0, '1h', '2026-03-08T18:36:22.520059'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2952,
    pnl_amount = -2.74,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AE19E5A88982CA0D', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2020-10-07 23:00:00', '2020-10-08 08:44:33', 523.55885315, 521.34831248,
    531.41223595, 510.46988182, 0.1061,
    0.4222, 4.48, 'TAKE_PROFIT', 9.74,
    1, '1h', '2026-03-08T18:36:22.520419'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4222,
    pnl_amount = 4.48,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '53C59718D5507FCA', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2020-10-08 17:00:00', '2020-10-09 01:20:14', 4174.68677099, 4201.44699899,
    4112.06646943, 4279.05394027, 0.1089,
    0.641, 6.98, 'TRAILING_STOP', 8.34,
    1, '1h', '2026-03-08T18:36:22.520354'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.641,
    pnl_amount = 6.98,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E285C4F0E06F9CC5', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2020-10-10 17:00:00', '2020-10-10 23:06:35', 3471.92984023, 3456.19211165,
    3524.00878784, 3385.13159423, 0.0855,
    0.4533, 3.88, 'TIME_EXIT', 6.11,
    1, '1h', '2026-03-08T18:36:22.520857'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4533,
    pnl_amount = 3.88,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4D37D2AA2D0F7288', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2020-10-26 02:00:00', '2020-10-26 12:10:58', 1774.46116023, 1762.87526969,
    1801.07807764, 1730.09963123, 0.0909,
    0.6529, 5.94, 'TRAILING_STOP', 10.18,
    1, '1h', '2026-03-08T18:36:22.518065'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6529,
    pnl_amount = 5.94,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '83EF7C437BC03076', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-11-03 07:00:00', '2020-11-03 12:16:46', 4315.8861861, 4298.91120156,
    4251.1478933, 4423.78334075, 0.0975,
    -0.3933, -3.83, 'TIME_EXIT', 5.28,
    0, '1h', '2026-03-08T18:36:22.518253'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3933,
    pnl_amount = -3.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B0CAE79979B852D4', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-11-03 13:00:00', '2020-11-03 15:17:39', 2518.06704292, 2537.24365352,
    2480.29603727, 2581.01871899, 0.1049,
    0.7616, 7.99, 'TIME_EXIT', 2.29,
    1, '1h', '2026-03-08T18:36:22.517825'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7616,
    pnl_amount = 7.99,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A6D71DCA390DCD5F', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2020-11-10 15:00:00', '2020-11-10 23:58:56', 58.19962291, 57.93260235,
    59.07261725, 56.74463234, 0.0889,
    0.4588, 4.08, 'TAKE_PROFIT', 8.98,
    1, '1h', '2026-03-08T18:36:22.522320'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4588,
    pnl_amount = 4.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3D4128111BC39F05', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2020-11-11 06:00:00', '2020-11-11 14:51:48', 4606.54758592, 4591.27813497,
    4537.44937213, 4721.71127557, 0.0901,
    -0.3315, -2.99, 'TIME_EXIT', 8.86,
    0, '1h', '2026-03-08T18:36:22.519132'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3315,
    pnl_amount = -2.99,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75CA2DC4843B7EE6', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2020-11-14 13:00:00', '2020-11-14 23:04:20', 4549.17848313, 4579.2463662,
    4480.94080589, 4662.90794521, 0.0948,
    0.661, 6.27, 'TAKE_PROFIT', 10.07,
    1, '1h', '2026-03-08T18:36:22.521449'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.661,
    pnl_amount = 6.27,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1AC9E268FBAB3625', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-11-17 01:00:00', '2020-11-17 07:33:48', 21273.03782897, 21188.38469493,
    21592.1333964, 20741.21188324, 0.0807,
    0.3979, 3.21, 'TRAILING_STOP', 6.56,
    1, '1h', '2026-03-08T18:36:22.517509'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3979,
    pnl_amount = 3.21,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '161C35A35E08D915', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2020-11-18 14:00:00', '2020-11-18 23:55:05', 1678.94914453, 1667.54539126,
    1704.1333817, 1636.97541592, 0.1132,
    0.6792, 7.69, 'TIME_EXIT', 9.92,
    1, '1h', '2026-03-08T18:36:22.519459'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6792,
    pnl_amount = 7.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D55D378AB51A7377', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-11-22 16:00:00', '2020-11-22 20:34:40', 3900.60991393, 3924.00938985,
    3842.10076522, 3998.12516178, 0.1087,
    0.5999, 6.52, 'TAKE_PROFIT', 4.58,
    1, '1h', '2026-03-08T18:36:22.518366'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5999,
    pnl_amount = 6.52,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DA52E3454182F552', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-11-24 09:00:00', '2020-11-24 16:01:43', 706.78144839, 711.60622663,
    696.17972666, 724.4509846, 0.0996,
    0.6826, 6.8, 'TRAILING_STOP', 7.03,
    1, '1h', '2026-03-08T18:36:22.519932'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6826,
    pnl_amount = 6.8,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BEC6D54FCDB5232C', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2020-11-30 09:00:00', '2020-11-30 16:49:38', 44437.8898022, 44724.00044823,
    43771.32145517, 45548.83704725, 0.0894,
    0.6438, 5.76, 'TRAILING_STOP', 7.83,
    1, '1h', '2026-03-08T18:36:22.519142'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6438,
    pnl_amount = 5.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '88F03455B1EEE95C', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2020-11-30 21:00:00', '2020-12-01 01:32:17', 3960.46753762, 3976.10802596,
    3901.06052456, 4059.47922606, 0.11,
    0.3949, 4.34, 'TRAILING_STOP', 4.54,
    1, '1h', '2026-03-08T18:36:22.521734'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3949,
    pnl_amount = 4.34,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C48D99560DFBA145', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2020-12-04 11:00:00', '2020-12-04 18:35:28', 182.28856162, 181.53416827,
    185.02289005, 177.73134758, 0.1144,
    0.4138, 4.74, 'TIME_EXIT', 7.59,
    1, '1h', '2026-03-08T18:36:22.523019'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4138,
    pnl_amount = 4.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CA140A175BF323A8', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2020-12-05 22:00:00', '2020-12-06 05:38:39', 1049.0570365, 1045.28142121,
    1033.32118095, 1075.28346241, 0.098,
    -0.3599, -3.53, 'STOP_LOSS', 7.64,
    0, '1h', '2026-03-08T18:36:22.522330'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3599,
    pnl_amount = -3.53,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '432FEDE5967D0B8F', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2020-12-08 17:00:00', '2020-12-09 00:25:24', 931.7429079, 937.86205726,
    917.76676428, 955.0364806, 0.093,
    0.6567, 6.11, 'TRAILING_STOP', 7.42,
    1, '1h', '2026-03-08T18:36:22.518898'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6567,
    pnl_amount = 6.11,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6307D562373BEF92', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2020-12-10 00:00:00', '2020-12-10 08:01:46', 955.43022242, 960.93213522,
    941.09876909, 979.31597798, 0.0811,
    0.5759, 4.67, 'TAKE_PROFIT', 8.03,
    1, '1h', '2026-03-08T18:36:22.518111'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5759,
    pnl_amount = 4.67,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2EE4A85B1330CDCC', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2020-12-14 07:00:00', '2020-12-14 18:55:49', 31127.61450824, 30898.55310838,
    31594.52872586, 30349.42414553, 0.1124,
    0.7359, 8.27, 'TAKE_PROFIT', 11.93,
    1, '1h', '2026-03-08T18:36:22.520600'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7359,
    pnl_amount = 8.27,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CB5029AAB0421DF0', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2020-12-15 01:00:00', '2020-12-15 04:27:32', 4997.02056181, 4972.06425213,
    5071.97587024, 4872.09504776, 0.1013,
    0.4994, 5.06, 'TRAILING_STOP', 3.46,
    1, '1h', '2026-03-08T18:36:22.521340'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4994,
    pnl_amount = 5.06,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C5E095CC193B427F', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2021-01-08 05:00:00', '2021-01-08 11:15:16', 323.67874659, 321.69901064,
    328.53392779, 315.58677792, 0.0903,
    0.6116, 5.52, 'TAKE_PROFIT', 6.25,
    1, '1h', '2026-03-08T18:36:22.521687'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6116,
    pnl_amount = 5.52,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '19F9363EB6337863', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-01-09 18:00:00', '2021-01-10 00:04:35', 2450.36842052, 2441.00464011,
    2413.61289421, 2511.62763103, 0.0861,
    -0.3821, -3.29, 'TIME_EXIT', 6.08,
    0, '1h', '2026-03-08T18:36:22.521614'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3821,
    pnl_amount = -3.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E12ECDABD3D76E6E', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2021-01-14 07:00:00', '2021-01-14 15:44:11', 471.10349967, 467.80408832,
    478.17005217, 459.32591218, 0.1084,
    0.7004, 7.59, 'TAKE_PROFIT', 8.74,
    1, '1h', '2026-03-08T18:36:22.521142'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7004,
    pnl_amount = 7.59,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AA44665120967D5B', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-01-17 06:00:00', '2021-01-17 10:58:37', 4340.83031139, 4307.44108598,
    4405.94276606, 4232.3095536, 0.1031,
    0.7692, 7.93, 'TAKE_PROFIT', 4.98,
    1, '1h', '2026-03-08T18:36:22.520050'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7692,
    pnl_amount = 7.93,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '880E3C9E8351171B', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2021-01-23 01:00:00', '2021-01-23 08:06:42', 620.33426472, 623.10462035,
    611.02925074, 635.84262133, 0.1119,
    0.4466, 5.0, 'TIME_EXIT', 7.11,
    1, '1h', '2026-03-08T18:36:22.522845'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4466,
    pnl_amount = 5.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8669768E4176F890', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-01-24 04:00:00', '2021-01-24 09:43:26', 2812.08928824, 2796.90487088,
    2854.27062756, 2741.78705603, 0.0809,
    0.54, 4.37, 'TRAILING_STOP', 5.72,
    1, '1h', '2026-03-08T18:36:22.522302'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.54,
    pnl_amount = 4.37,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F743BC2F61A690BE', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-01-29 14:00:00', '2021-01-30 01:15:37', 32492.54017623, 32365.04432761,
    32979.92827888, 31680.22667183, 0.0892,
    0.3924, 3.5, 'TAKE_PROFIT', 11.26,
    1, '1h', '2026-03-08T18:36:22.517558'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3924,
    pnl_amount = 3.5,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7302E86147549BE3', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-02-01 14:00:00', '2021-02-01 16:24:50', 1694.77531601, 1700.60256218,
    1720.19694575, 1652.40593311, 0.1094,
    -0.3438, -3.76, 'TIME_EXIT', 2.41,
    0, '1h', '2026-03-08T18:36:22.516921'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3438,
    pnl_amount = -3.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '028746E10172F436', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-02-01 14:00:00', '2021-02-02 00:10:31', 4021.16512892, 4008.62799868,
    3960.84765199, 4121.69425714, 0.0918,
    -0.3118, -2.86, 'TIME_EXIT', 10.18,
    0, '1h', '2026-03-08T18:36:22.517033'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3118,
    pnl_amount = -2.86,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BE04C7FB850674A0', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-02-03 09:00:00', '2021-02-03 11:47:10', 1365.91661307, 1360.90372316,
    1345.42786387, 1400.0645284, 0.1148,
    -0.367, -4.21, 'TIME_EXIT', 2.79,
    0, '1h', '2026-03-08T18:36:22.521208'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.367,
    pnl_amount = -4.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0D5451EE9169D520', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2021-02-06 13:00:00', '2021-02-07 00:59:49', 1647.41061757, 1657.02016175,
    1622.69945831, 1688.59588301, 0.0903,
    0.5833, 5.27, 'TRAILING_STOP', 12.0,
    1, '1h', '2026-03-08T18:36:22.517663'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5833,
    pnl_amount = 5.27,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C7D923620DC092B3', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-02-09 07:00:00', '2021-02-09 11:34:30', 3657.89791762, 3639.35855308,
    3712.76638638, 3566.45046968, 0.1094,
    0.5068, 5.55, 'TRAILING_STOP', 4.58,
    1, '1h', '2026-03-08T18:36:22.521547'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5068,
    pnl_amount = 5.55,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '07BC9AF4927CEEC3', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2021-02-16 20:00:00', '2021-02-17 02:58:11', 2502.05749846, 2512.41000624,
    2539.58836093, 2439.506061, 0.0837,
    -0.4138, -3.46, 'TIME_EXIT', 6.97,
    0, '1h', '2026-03-08T18:36:22.521012'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4138,
    pnl_amount = -3.46,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '967728A3950B68C5', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-02-17 01:00:00', '2021-02-17 04:43:46', 23268.74629403, 23428.1788561,
    22919.71509962, 23850.46495138, 0.0948,
    0.6852, 6.5, 'TAKE_PROFIT', 3.73,
    1, '1h', '2026-03-08T18:36:22.518934'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6852,
    pnl_amount = 6.5,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8024E03D8AB30C88', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2021-02-18 21:00:00', '2021-02-18 23:41:05', 3209.17347224, 3220.63233913,
    3257.31107433, 3128.94413544, 0.0869,
    -0.3571, -3.1, 'TIME_EXIT', 2.68,
    0, '1h', '2026-03-08T18:36:22.521972'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3571,
    pnl_amount = -3.1,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '04674022A87C4684', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-02-18 23:00:00', '2021-02-19 07:14:01', 49.01851871, 48.72309372,
    49.75379649, 47.79305574, 0.1084,
    0.6027, 6.53, 'TAKE_PROFIT', 8.23,
    1, '1h', '2026-03-08T18:36:22.522991'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6027,
    pnl_amount = 6.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8F2DBB1C0A3D0B3F', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-02-20 13:00:00', '2021-02-20 16:59:47', 10437.06936597, 10471.42491134,
    10593.62540646, 10176.14263182, 0.0853,
    -0.3292, -2.81, 'TIME_EXIT', 4.0,
    0, '1h', '2026-03-08T18:36:22.522339'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3292,
    pnl_amount = -2.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1D98D8EEAD3A08CA', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-02-23 15:00:00', '2021-02-24 01:45:01', 4182.58819409, 4199.96790854,
    4245.327017, 4078.02348924, 0.0945,
    -0.4155, -3.93, 'TIME_EXIT', 10.75,
    0, '1h', '2026-03-08T18:36:22.518521'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4155,
    pnl_amount = -3.93,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1EB22AEAFAB77F49', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-02-24 11:00:00', '2021-02-24 17:13:32', 32199.55671734, 31957.71862228,
    32682.5500681, 31394.56779941, 0.1188,
    0.7511, 8.92, 'TRAILING_STOP', 6.23,
    1, '1h', '2026-03-08T18:36:22.517672'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7511,
    pnl_amount = 8.92,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '69786F669635108B', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2021-02-27 17:00:00', '2021-02-28 01:06:19', 4908.73057704, 4945.58585477,
    4835.09961839, 5031.44884147, 0.0826,
    0.7508, 6.2, 'TRAILING_STOP', 8.11,
    1, '1h', '2026-03-08T18:36:22.523127'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7508,
    pnl_amount = 6.2,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A6104BCBF8D22D5B', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-03-11 18:00:00', '2021-03-11 20:45:40', 4252.52373436, 4236.77287534,
    4188.73587835, 4358.83682772, 0.0928,
    -0.3704, -3.44, 'STOP_LOSS', 2.76,
    0, '1h', '2026-03-08T18:36:22.518177'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3704,
    pnl_amount = -3.44,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EF2B54571CFC0716', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2021-03-17 09:00:00', '2021-03-17 11:08:17', 2008.53693017, 1993.20844445,
    2038.66498413, 1958.32350692, 0.1036,
    0.7632, 7.91, 'TIME_EXIT', 2.14,
    1, '1h', '2026-03-08T18:36:22.517852'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7632,
    pnl_amount = 7.91,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '70045BCC9D475B74', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2021-03-19 02:00:00', '2021-03-19 13:25:36', 2063.3679626, 2056.92640196,
    2032.41744316, 2114.95216167, 0.1018,
    -0.3122, -3.18, 'TIME_EXIT', 11.43,
    0, '1h', '2026-03-08T18:36:22.518147'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3122,
    pnl_amount = -3.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '11ACF832907A83FC', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2021-03-22 10:00:00', '2021-03-22 18:19:44', 3370.38164005, 3357.38526532,
    3319.82591545, 3454.64118105, 0.1023,
    -0.3856, -3.95, 'STOP_LOSS', 8.33,
    0, '1h', '2026-03-08T18:36:22.519793'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3856,
    pnl_amount = -3.95,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AAED2FD589094760', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2021-04-06 11:00:00', '2021-04-06 19:32:28', 1874.25422381, 1860.67844642,
    1902.36803716, 1827.39786821, 0.109,
    0.7243, 7.89, 'TAKE_PROFIT', 8.54,
    1, '1h', '2026-03-08T18:36:22.519497'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7243,
    pnl_amount = 7.89,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FE0B1C4C072774CD', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2021-04-08 12:00:00', '2021-04-08 18:06:12', 3161.51647347, 3140.95742002,
    3208.93922057, 3082.47856163, 0.0977,
    0.6503, 6.36, 'TAKE_PROFIT', 6.1,
    1, '1h', '2026-03-08T18:36:22.517727'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6503,
    pnl_amount = 6.36,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '210BDF67AC4D36C3', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2021-04-13 07:00:00', '2021-04-13 13:47:45', 2639.49291706, 2620.97172105,
    2679.08531081, 2573.50559413, 0.1123,
    0.7017, 7.88, 'TIME_EXIT', 6.8,
    1, '1h', '2026-03-08T18:36:22.517054'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7017,
    pnl_amount = 7.88,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '973C8686A79DBE63', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-04-13 21:00:00', '2021-04-14 06:35:54', 36199.26425486, 36074.11247257,
    35656.27529104, 37104.24586123, 0.0953,
    -0.3457, -3.3, 'STOP_LOSS', 9.6,
    0, '1h', '2026-03-08T18:36:22.521538'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3457,
    pnl_amount = -3.3,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '41459F8ED7CB5F6E', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2021-04-14 20:00:00', '2021-04-15 00:46:42', 2823.10180266, 2801.94385445,
    2865.4483297, 2752.52425759, 0.1149,
    0.7495, 8.61, 'TIME_EXIT', 4.78,
    1, '1h', '2026-03-08T18:36:22.517043'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7495,
    pnl_amount = 8.61,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0AFF2476DB4C606C', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2021-04-15 10:00:00', '2021-04-15 17:38:09', 266.46604832, 265.26368695,
    270.46303905, 259.80439711, 0.0864,
    0.4512, 3.9, 'TRAILING_STOP', 7.64,
    1, '1h', '2026-03-08T18:36:22.519515'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4512,
    pnl_amount = 3.9,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CEA748E780FAB856', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2021-04-16 10:00:00', '2021-04-16 21:31:14', 4326.46666213, 4356.24309954,
    4261.5696622, 4434.62832868, 0.0958,
    0.6882, 6.59, 'TRAILING_STOP', 11.52,
    1, '1h', '2026-03-08T18:36:22.518447'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6882,
    pnl_amount = 6.59,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A520294BD1BCB21', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2021-04-16 19:00:00', '2021-04-17 02:48:02', 1126.63611866, 1130.76866514,
    1143.53566044, 1098.47021569, 0.0919,
    -0.3668, -3.37, 'STOP_LOSS', 7.8,
    0, '1h', '2026-03-08T18:36:22.521218'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3668,
    pnl_amount = -3.37,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5F67BB63C6B873A8', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2021-04-18 08:00:00', '2021-04-18 18:15:08', 3131.8439956, 3113.09423403,
    3178.82165554, 3053.54789571, 0.0951,
    0.5987, 5.69, 'TIME_EXIT', 10.25,
    1, '1h', '2026-03-08T18:36:22.522132'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5987,
    pnl_amount = 5.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD38AB2154E33D94', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-04-18 16:00:00', '2021-04-19 01:59:58', 4772.66191854, 4788.1656949,
    4844.25184732, 4653.34537058, 0.1025,
    -0.3248, -3.33, 'STOP_LOSS', 10.0,
    0, '1h', '2026-03-08T18:36:22.521928'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3248,
    pnl_amount = -3.33,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '366FF4129A8B7B16', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2021-04-29 20:00:00', '2021-04-30 03:44:12', 4418.42679551, 4433.41503101,
    4484.70319744, 4307.96612562, 0.1157,
    -0.3392, -3.92, 'TIME_EXIT', 7.74,
    0, '1h', '2026-03-08T18:36:22.520041'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3392,
    pnl_amount = -3.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '589DE46527E4726B', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-05-06 03:00:00', '2021-05-06 08:24:20', 28930.82514544, 29099.3112194,
    28496.86276826, 29654.09577408, 0.1122,
    0.5824, 6.53, 'TRAILING_STOP', 5.41,
    1, '1h', '2026-03-08T18:36:22.519431'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5824,
    pnl_amount = 6.53,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D56C83B78ADA956D', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2021-05-09 16:00:00', '2021-05-09 22:27:23', 492.99320536, 495.05470835,
    485.59830728, 505.31803549, 0.108,
    0.4182, 4.52, 'TIME_EXIT', 6.46,
    1, '1h', '2026-03-08T18:36:22.517088'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4182,
    pnl_amount = 4.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '32C09F806EACEAAD', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-05-12 12:00:00', '2021-05-12 16:55:51', 5061.77221661, 5077.10387359,
    5137.69879986, 4935.2279112, 0.1121,
    -0.3029, -3.39, 'TIME_EXIT', 4.93,
    0, '1h', '2026-03-08T18:36:22.519346'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3029,
    pnl_amount = -3.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B48D24625DB62DF8', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-05-12 18:00:00', '2021-05-12 22:02:52', 1228.28385621, 1220.73484858,
    1246.70811405, 1197.5767598, 0.1171,
    0.6146, 7.2, 'TIME_EXIT', 4.05,
    1, '1h', '2026-03-08T18:36:22.523203'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6146,
    pnl_amount = 7.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F13F3E0B640364B6', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-05-17 06:00:00', '2021-05-17 09:30:53', 38638.05995033, 38799.24878697,
    38058.48905107, 39604.01144908, 0.0829,
    0.4172, 3.46, 'TAKE_PROFIT', 3.51,
    1, '1h', '2026-03-08T18:36:22.519292'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4172,
    pnl_amount = 3.46,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6251D55B4D61A533', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-05-18 11:00:00', '2021-05-18 17:03:03', 6124.76799197, 6092.29890887,
    6216.63951185, 5971.64879217, 0.0943,
    0.5301, 5.0, 'TRAILING_STOP', 6.05,
    1, '1h', '2026-03-08T18:36:22.519328'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5301,
    pnl_amount = 5.0,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0F84AA0F929A9F3A', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-05-18 17:00:00', '2021-05-18 21:21:07', 41499.85948418, 41241.6633324,
    42122.35737644, 40462.36299707, 0.1093,
    0.6222, 6.8, 'TIME_EXIT', 4.35,
    1, '1h', '2026-03-08T18:36:22.520618'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6222,
    pnl_amount = 6.8,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '231A05EBEE65E142', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2021-05-23 22:00:00', '2021-05-24 06:36:23', 130.43951584, 131.08381003,
    128.4829231, 133.70050373, 0.1144,
    0.4939, 5.65, 'TRAILING_STOP', 8.61,
    1, '1h', '2026-03-08T18:36:22.521002'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4939,
    pnl_amount = 5.65,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8790E5E851E96ED1', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-05-24 22:00:00', '2021-05-25 06:32:39', 3590.75592499, 3564.81865759,
    3644.61726387, 3500.98702687, 0.1093,
    0.7223, 7.9, 'TIME_EXIT', 8.54,
    1, '1h', '2026-03-08T18:36:22.520875'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7223,
    pnl_amount = 7.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E0766834F616D843', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-05-26 06:00:00', '2021-05-26 14:45:43', 26397.88013855, 26507.38603235,
    26001.91193648, 27057.82714202, 0.0824,
    0.4148, 3.42, 'TAKE_PROFIT', 8.76,
    1, '1h', '2026-03-08T18:36:22.517110'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4148,
    pnl_amount = 3.42,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '935F1A1443336472', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-05-28 14:00:00', '2021-05-28 16:36:57', 3483.8320038, 3465.36239171,
    3536.08948386, 3396.73620371, 0.086,
    0.5302, 4.56, 'TIME_EXIT', 2.62,
    1, '1h', '2026-03-08T18:36:22.523072'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5302,
    pnl_amount = 4.56,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D1C31F41220A54AA', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2021-05-30 23:00:00', '2021-05-31 09:48:48', 1220.97901277, 1214.22176454,
    1239.29369797, 1190.45453745, 0.0831,
    0.5534, 4.6, 'TIME_EXIT', 10.81,
    1, '1h', '2026-03-08T18:36:22.519740'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5534,
    pnl_amount = 4.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1F6D1C7BCF8D047C', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2021-06-05 17:00:00', '2021-06-05 20:22:14', 269.96607776, 271.27931155,
    265.91658659, 276.71522971, 0.1053,
    0.4864, 5.12, 'TRAILING_STOP', 3.37,
    1, '1h', '2026-03-08T18:36:22.518512'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4864,
    pnl_amount = 5.12,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D4E0092EB3DDD10E', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-06-12 23:00:00', '2021-06-13 04:48:46', 789.53957993, 786.32604299,
    801.38267363, 769.80109043, 0.1131,
    0.407, 4.6, 'TIME_EXIT', 5.81,
    1, '1h', '2026-03-08T18:36:22.517160'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.407,
    pnl_amount = 4.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C0E941C676BC55A9', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-06-14 06:00:00', '2021-06-14 13:53:21', 42471.30653783, 42598.08876372,
    43108.3761359, 41409.52387438, 0.1044,
    -0.2985, -3.12, 'STOP_LOSS', 7.89,
    0, '1h', '2026-03-08T18:36:22.518138'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2985,
    pnl_amount = -3.12,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4822090EAE34A333', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2021-06-19 10:00:00', '2021-06-19 15:34:38', 877.96106487, 873.31698809,
    891.13048085, 856.01203825, 0.0949,
    0.529, 5.02, 'TRAILING_STOP', 5.58,
    1, '1h', '2026-03-08T18:36:22.518384'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.529,
    pnl_amount = 5.02,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '172C0FA4323C200A', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-06-24 22:00:00', '2021-06-25 04:31:34', 534.12578125, 530.65790522,
    542.13766797, 520.77263672, 0.1026,
    0.6493, 6.66, 'TRAILING_STOP', 6.53,
    1, '1h', '2026-03-08T18:36:22.519685'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6493,
    pnl_amount = 6.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BCA6326D038B7C01', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-06-25 15:00:00', '2021-06-25 18:27:37', 2736.67036997, 2756.59786644,
    2695.62031442, 2805.08712922, 0.1122,
    0.7282, 8.17, 'TRAILING_STOP', 3.46,
    1, '1h', '2026-03-08T18:36:22.522434'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7282,
    pnl_amount = 8.17,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BCA9AEFA22A1B8BA', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-06-25 16:00:00', '2021-06-25 21:49:51', 1129.16327624, 1120.52465817,
    1146.10072539, 1100.93419434, 0.1185,
    0.765, 9.07, 'TIME_EXIT', 5.83,
    1, '1h', '2026-03-08T18:36:22.521418'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.765,
    pnl_amount = 9.07,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8AE3B33DA4DA5D5F', 'BB_SQUEEZE_v1', 'BNBUSDT', 'SHORT',
    '2021-06-25 21:00:00', '2021-06-26 01:14:35', 3778.68317872, 3794.29656078,
    3835.3634264, 3684.21609925, 0.1185,
    -0.4132, -4.9, 'TIME_EXIT', 4.24,
    0, '1h', '2026-03-08T18:36:22.518590'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4132,
    pnl_amount = -4.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FCBC4628ACC5A279', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2021-06-26 18:00:00', '2021-06-26 22:52:38', 3791.74629327, 3817.4180466,
    3734.87009888, 3886.53995061, 0.1083,
    0.677, 7.33, 'TAKE_PROFIT', 4.88,
    1, '1h', '2026-03-08T18:36:22.519169'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.677,
    pnl_amount = 7.33,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AFE3919FD512D7BE', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-07-04 22:00:00', '2021-07-05 07:27:33', 37260.72723304, 37069.63116621,
    37819.63814154, 36329.20905222, 0.1144,
    0.5129, 5.86, 'TRAILING_STOP', 9.46,
    1, '1h', '2026-03-08T18:36:22.522917'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5129,
    pnl_amount = 5.86,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '26428A45A70DCCAB', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2021-07-11 18:00:00', '2021-07-12 03:30:19', 2573.70075101, 2562.54947215,
    2612.30626228, 2509.35823224, 0.1036,
    0.4333, 4.49, 'TIME_EXIT', 9.51,
    1, '1h', '2026-03-08T18:36:22.521521'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4333,
    pnl_amount = 4.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7D59DECC11553281', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2021-07-16 10:00:00', '2021-07-16 19:53:34', 1947.05147023, 1955.0595534,
    1917.84569818, 1995.72775699, 0.0804,
    0.4113, 3.31, 'TIME_EXIT', 9.89,
    1, '1h', '2026-03-08T18:36:22.519178'
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
    'BCB73949BE102981', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2021-07-19 18:00:00', '2021-07-20 01:30:51', 3210.99959887, 3232.66044619,
    3162.83460489, 3291.27458885, 0.1177,
    0.6746, 7.94, 'TAKE_PROFIT', 7.51,
    1, '1h', '2026-03-08T18:36:22.517806'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6746,
    pnl_amount = 7.94,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '641A3AA24C046B17', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2021-07-21 06:00:00', '2021-07-21 12:34:03', 4141.1882895, 4128.36476428,
    4079.07046516, 4244.71799674, 0.1037,
    -0.3097, -3.21, 'TIME_EXIT', 6.57,
    0, '1h', '2026-03-08T18:36:22.520095'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3097,
    pnl_amount = -3.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EC49BE08110F32B4', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-07-22 13:00:00', '2021-07-22 21:39:14', 37321.11961471, 37167.41431953,
    37880.93640893, 36388.09162434, 0.1133,
    0.4118, 4.67, 'TIME_EXIT', 8.65,
    1, '1h', '2026-03-08T18:36:22.523321'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4118,
    pnl_amount = 4.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '849EE60AE32FE89D', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-07-25 02:00:00', '2021-07-25 12:59:11', 15557.37827312, 15614.5561367,
    15790.73894722, 15168.44381629, 0.0817,
    -0.3675, -3.0, 'TIME_EXIT', 10.99,
    0, '1h', '2026-03-08T18:36:22.523339'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3675,
    pnl_amount = -3.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '956FDC6B74C5EF87', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2021-07-25 17:00:00', '2021-07-25 22:58:42', 4899.90410646, 4876.62708258,
    4973.40266806, 4777.4065038, 0.1009,
    0.4751, 4.79, 'TRAILING_STOP', 5.98,
    1, '1h', '2026-03-08T18:36:22.518658'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4751,
    pnl_amount = 4.79,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '61FC9432226E7838', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-07-29 19:00:00', '2021-07-29 23:40:56', 823.81520789, 820.84241517,
    811.45797978, 844.41058809, 0.0929,
    -0.3609, -3.35, 'STOP_LOSS', 4.68,
    0, '1h', '2026-03-08T18:36:22.518889'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3609,
    pnl_amount = -3.35,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D7A9F749F9BC7EF4', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-08-02 14:00:00', '2021-08-02 20:22:45', 3869.9280218, 3850.16333825,
    3927.97694212, 3773.17982125, 0.1142,
    0.5107, 5.83, 'TIME_EXIT', 6.38,
    1, '1h', '2026-03-08T18:36:22.522065'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5107,
    pnl_amount = 5.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1376DBD35BCF036C', 'BB_SQUEEZE_v1', 'BNBUSDT', 'SHORT',
    '2021-08-03 11:00:00', '2021-08-03 14:14:38', 3334.03915459, 3309.69566505,
    3384.04974191, 3250.68817572, 0.0884,
    0.7302, 6.46, 'TRAILING_STOP', 3.24,
    1, '1h', '2026-03-08T18:36:22.522653'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7302,
    pnl_amount = 6.46,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C442948AA015FBBA', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-08-07 11:00:00', '2021-08-07 21:40:10', 10041.33777548, 10010.5698741,
    9890.71770885, 10292.37121987, 0.1012,
    -0.3064, -3.1, 'TIME_EXIT', 10.67,
    0, '1h', '2026-03-08T18:36:22.522698'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3064,
    pnl_amount = -3.1,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ADA6C24A2FD3223C', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2021-08-10 01:00:00', '2021-08-10 06:24:54', 2878.72875819, 2887.44002899,
    2921.90968956, 2806.76053923, 0.1049,
    -0.3026, -3.18, 'TIME_EXIT', 5.42,
    0, '1h', '2026-03-08T18:36:22.522963'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3026,
    pnl_amount = -3.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EDBEFEF61508682B', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-08-10 02:00:00', '2021-08-10 08:41:35', 3174.94537626, 3165.07248169,
    3127.32119561, 3254.31901066, 0.1149,
    -0.311, -3.57, 'STOP_LOSS', 6.69,
    0, '1h', '2026-03-08T18:36:22.519588'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.311,
    pnl_amount = -3.57,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2DB496ADB08CA5C5', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2021-08-10 20:00:00', '2021-08-11 03:07:33', 371.28434565, 370.12615509,
    365.71508047, 380.56645429, 0.0936,
    -0.3119, -2.92, 'TIME_EXIT', 7.13,
    0, '1h', '2026-03-08T18:36:22.521855'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3119,
    pnl_amount = -2.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '922F61F3CA2ED749', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2021-08-12 09:00:00', '2021-08-12 20:09:04', 3150.99451673, 3174.57870062,
    3103.72959898, 3229.76937965, 0.1067,
    0.7485, 7.99, 'TRAILING_STOP', 11.15,
    1, '1h', '2026-03-08T18:36:22.517427'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7485,
    pnl_amount = 7.99,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0709FE46851DEEC7', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2021-08-16 13:00:00', '2021-08-16 21:31:58', 1314.54423969, 1309.30177434,
    1294.82607609, 1347.40784568, 0.1131,
    -0.3988, -4.51, 'STOP_LOSS', 8.53,
    0, '1h', '2026-03-08T18:36:22.521169'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3988,
    pnl_amount = -4.51,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A63CFEAE6219281D', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2021-08-22 15:00:00', '2021-08-23 01:17:26', 3913.45180451, 3887.32665703,
    3972.15358158, 3815.6155094, 0.098,
    0.6676, 6.54, 'TIME_EXIT', 10.29,
    1, '1h', '2026-03-08T18:36:22.521574'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6676,
    pnl_amount = 6.54,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ED8B55BC232A5707', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-08-25 02:00:00', '2021-08-25 05:12:35', 4002.46899254, 4020.69184867,
    3942.43195765, 4102.53071735, 0.0834,
    0.4553, 3.8, 'TRAILING_STOP', 3.21,
    1, '1h', '2026-03-08T18:36:22.519319'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4553,
    pnl_amount = 3.8,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10429A45EE4D37F9', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2021-08-26 16:00:00', '2021-08-27 02:14:53', 4153.82069062, 4141.50067657,
    4091.51338026, 4257.66620789, 0.0931,
    -0.2966, -2.76, 'TIME_EXIT', 10.25,
    0, '1h', '2026-03-08T18:36:22.518074'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2966,
    pnl_amount = -2.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D7E4FE59FC0B02DD', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-08-30 22:00:00', '2021-08-31 06:26:13', 2808.7200431, 2819.56457013,
    2766.58924245, 2878.93804417, 0.1098,
    0.3861, 4.24, 'TIME_EXIT', 8.44,
    1, '1h', '2026-03-08T18:36:22.520747'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3861,
    pnl_amount = 4.24,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '601E56176902384E', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-08-31 03:00:00', '2021-08-31 07:27:52', 47847.61147105, 47507.4500417,
    48565.32564311, 46651.42118427, 0.0842,
    0.7109, 5.99, 'TRAILING_STOP', 4.46,
    1, '1h', '2026-03-08T18:36:22.517390'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7109,
    pnl_amount = 5.99,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '995890001AC09078', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-09-06 15:00:00', '2021-09-06 17:58:01', 1825.80401677, 1817.69637737,
    1853.19107703, 1780.15891636, 0.0918,
    0.4441, 4.08, 'TAKE_PROFIT', 2.97,
    1, '1h', '2026-03-08T18:36:22.523064'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4441,
    pnl_amount = 4.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '47CAC84D6CCEB381', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2021-09-07 18:00:00', '2021-09-08 00:24:51', 1527.81721452, 1538.35467825,
    1504.8999563, 1566.01264489, 0.0905,
    0.6897, 6.24, 'TAKE_PROFIT', 6.41,
    1, '1h', '2026-03-08T18:36:22.522442'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6897,
    pnl_amount = 6.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F8806C5794A2C821', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-09-10 10:00:00', '2021-09-10 18:49:28', 3409.79784673, 3433.93840049,
    3358.65087903, 3495.0427929, 0.1079,
    0.708, 7.64, 'TAKE_PROFIT', 8.82,
    1, '1h', '2026-03-08T18:36:22.517399'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.708,
    pnl_amount = 7.64,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AF0D272CACFB226D', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2021-09-12 16:00:00', '2021-09-12 19:47:15', 3172.07182164, 3182.05321128,
    3219.65289897, 3092.7700261, 0.1064,
    -0.3147, -3.35, 'STOP_LOSS', 3.79,
    0, '1h', '2026-03-08T18:36:22.521826'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3147,
    pnl_amount = -3.35,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D5164F42BC2E61ED', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2021-09-14 16:00:00', '2021-09-14 21:46:46', 530.16386266, 533.57600107,
    522.21140472, 543.41795923, 0.1175,
    0.6436, 7.56, 'TAKE_PROFIT', 5.78,
    1, '1h', '2026-03-08T18:36:22.519833'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6436,
    pnl_amount = 7.56,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4FAD944EF20609E1', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2021-09-16 20:00:00', '2021-09-17 07:45:03', 3770.39503016, 3743.00516365,
    3826.95095562, 3676.13515441, 0.114,
    0.7264, 8.28, 'TRAILING_STOP', 11.75,
    1, '1h', '2026-03-08T18:36:22.520560'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7264,
    pnl_amount = 8.28,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9469F187EDAF08AA', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-09-16 21:00:00', '2021-09-17 05:00:59', 158.74160957, 159.61006107,
    156.36048542, 162.71014981, 0.0974,
    0.5471, 5.33, 'TAKE_PROFIT', 8.02,
    1, '1h', '2026-03-08T18:36:22.522186'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5471,
    pnl_amount = 5.33,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CC5FD4BA38CC8B03', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-09-17 10:00:00', '2021-09-17 20:49:18', 2934.05380897, 2915.40218288,
    2978.0646161, 2860.70246374, 0.1037,
    0.6357, 6.59, 'TAKE_PROFIT', 10.82,
    1, '1h', '2026-03-08T18:36:22.522623'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6357,
    pnl_amount = 6.59,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '601035DE06AABE92', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2021-09-18 14:00:00', '2021-09-18 23:43:40', 1166.43651513, 1162.11786727,
    1148.9399674, 1195.59742801, 0.0837,
    -0.3702, -3.1, 'STOP_LOSS', 9.73,
    0, '1h', '2026-03-08T18:36:22.521312'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3702,
    pnl_amount = -3.1,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C18E8576666C8E89', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-09-20 19:00:00', '2021-09-20 21:39:12', 1188.88910194, 1182.76729694,
    1206.72243847, 1159.16687439, 0.095,
    0.5149, 4.89, 'TRAILING_STOP', 2.65,
    1, '1h', '2026-03-08T18:36:22.519025'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5149,
    pnl_amount = 4.89,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5D05919DF41B86D0', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2021-09-22 10:00:00', '2021-09-22 12:39:07', 28.9598924, 28.74625143,
    29.39429078, 28.23589509, 0.1084,
    0.7377, 7.99, 'TAKE_PROFIT', 2.65,
    1, '1h', '2026-03-08T18:36:22.520077'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7377,
    pnl_amount = 7.99,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10584B9C2F8242EB', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-09-24 22:00:00', '2021-09-25 03:10:17', 3507.49918104, 3496.34589112,
    3454.88669333, 3595.18666057, 0.0842,
    -0.318, -2.68, 'STOP_LOSS', 5.17,
    0, '1h', '2026-03-08T18:36:22.522855'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.318,
    pnl_amount = -2.68,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7A4DC7A8DBF6DCE7', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-09-25 01:00:00', '2021-09-25 12:36:45', 714.36548175, 717.97277217,
    703.64999953, 732.2246188, 0.091,
    0.505, 4.6, 'TIME_EXIT', 11.61,
    1, '1h', '2026-03-08T18:36:22.518028'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.505,
    pnl_amount = 4.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2DFF7EFBA4C83592', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2021-10-01 17:00:00', '2021-10-02 02:49:52', 3901.16793966, 3880.36578693,
    3959.68545876, 3803.63874117, 0.1172,
    0.5332, 6.25, 'TAKE_PROFIT', 9.83,
    1, '1h', '2026-03-08T18:36:22.518347'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5332,
    pnl_amount = 6.25,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '135EC3E9E4C7DFFC', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-10-02 20:00:00', '2021-10-03 04:25:10', 25094.84555564, 24946.97304254,
    25471.26823897, 24467.47441675, 0.1056,
    0.5893, 6.22, 'TAKE_PROFIT', 8.42,
    1, '1h', '2026-03-08T18:36:22.522872'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5893,
    pnl_amount = 6.22,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AF77A23EE60ECADE', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2021-10-03 16:00:00', '2021-10-03 18:23:31', 2540.31866356, 2527.21209553,
    2578.42344352, 2476.81069697, 0.0812,
    0.5159, 4.19, 'TRAILING_STOP', 2.39,
    1, '1h', '2026-03-08T18:36:22.521836'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5159,
    pnl_amount = 4.19,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '130D906F150BCBB1', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-10-06 16:00:00', '2021-10-07 00:10:55', 30663.27224367, 30459.39275958,
    31123.22132732, 29896.69043758, 0.1066,
    0.6649, 7.09, 'TIME_EXIT', 8.18,
    1, '1h', '2026-03-08T18:36:22.521188'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6649,
    pnl_amount = 7.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CBF8A7868BE9A638', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-10-11 08:00:00', '2021-10-11 16:50:12', 2192.5182137, 2177.94935991,
    2225.4059869, 2137.70525836, 0.0871,
    0.6645, 5.78, 'TAKE_PROFIT', 8.84,
    1, '1h', '2026-03-08T18:36:22.517261'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6645,
    pnl_amount = 5.78,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2D5837FCB3E62EB9', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-10-11 14:00:00', '2021-10-11 22:49:38', 2300.89127995, 2315.79198931,
    2266.37791075, 2358.41356194, 0.1192,
    0.6476, 7.72, 'TIME_EXIT', 8.83,
    1, '1h', '2026-03-08T18:36:22.519872'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6476,
    pnl_amount = 7.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F23B03736116FE7A', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2021-10-11 20:00:00', '2021-10-12 06:01:32', 2982.26513729, 2992.74231233,
    3026.99911435, 2907.70850886, 0.1169,
    -0.3513, -4.11, 'STOP_LOSS', 10.03,
    0, '1h', '2026-03-08T18:36:22.518954'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3513,
    pnl_amount = -4.11,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '505344072ACB4982', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2021-10-12 23:00:00', '2021-10-13 03:12:47', 3845.342705, 3833.85608007,
    3787.66256443, 3941.47627263, 0.0837,
    -0.2987, -2.5, 'TIME_EXIT', 4.21,
    0, '1h', '2026-03-08T18:36:22.517500'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2987,
    pnl_amount = -2.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A8A0927939AA4C83', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2021-10-17 02:00:00', '2021-10-17 08:05:23', 2594.27917441, 2584.96196876,
    2555.36498679, 2659.13615377, 0.0923,
    -0.3591, -3.32, 'STOP_LOSS', 6.09,
    0, '1h', '2026-03-08T18:36:22.522274'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3591,
    pnl_amount = -3.32,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3D320173CE0B3D35', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2021-10-21 23:00:00', '2021-10-22 06:37:17', 4203.81952001, 4175.12000112,
    4266.87681281, 4098.72403201, 0.097,
    0.6827, 6.62, 'TAKE_PROFIT', 7.62,
    1, '1h', '2026-03-08T18:36:22.521440'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6827,
    pnl_amount = 6.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9CEA90E200D73882', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-10-22 17:00:00', '2021-10-23 01:54:05', 3613.06597716, 3636.11638343,
    3558.8699875, 3703.39262659, 0.0883,
    0.638, 5.63, 'TIME_EXIT', 8.9,
    1, '1h', '2026-03-08T18:36:22.520455'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.638,
    pnl_amount = 5.63,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '974108C96FF3E26F', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-10-24 09:00:00', '2021-10-24 15:42:23', 44693.94292331, 44869.47545375,
    44023.53377946, 45811.29149639, 0.0846,
    0.3927, 3.32, 'TRAILING_STOP', 6.71,
    1, '1h', '2026-03-08T18:36:22.519812'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3927,
    pnl_amount = 3.32,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '975C5A5950A48D9F', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2021-10-31 08:00:00', '2021-10-31 11:06:44', 3073.16470738, 3090.9475917,
    3027.06723677, 3149.99382507, 0.1024,
    0.5787, 5.92, 'TIME_EXIT', 3.11,
    1, '1h', '2026-03-08T18:36:22.521133'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5787,
    pnl_amount = 5.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4ED53288FD0B1269', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2021-11-01 09:00:00', '2021-11-01 13:10:05', 4783.80463366, 4753.67809163,
    4855.56170316, 4664.20951782, 0.1012,
    0.6298, 6.37, 'TAKE_PROFIT', 4.17,
    1, '1h', '2026-03-08T18:36:22.519643'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6298,
    pnl_amount = 6.37,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '43EC16EBA629E044', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-11-06 23:00:00', '2021-11-07 10:04:03', 955.47267455, 958.37093127,
    969.80476467, 931.58585768, 0.0934,
    -0.3033, -2.83, 'TIME_EXIT', 11.07,
    0, '1h', '2026-03-08T18:36:22.519310'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3033,
    pnl_amount = -2.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AF42A4A533DD2A0D', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-11-08 01:00:00', '2021-11-08 06:25:19', 3460.0509237, 3477.42167559,
    3408.15015985, 3546.5521968, 0.0904,
    0.502, 4.54, 'TAKE_PROFIT', 5.42,
    1, '1h', '2026-03-08T18:36:22.521846'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.502,
    pnl_amount = 4.54,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D4C7AC044469E3A5', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2021-11-08 02:00:00', '2021-11-08 10:12:32', 4974.03082935, 4954.28606615,
    4899.42036691, 5098.38160009, 0.0936,
    -0.397, -3.71, 'STOP_LOSS', 8.21,
    0, '1h', '2026-03-08T18:36:22.520140'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.397,
    pnl_amount = -3.71,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5B68A4960FEC7D6B', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-11-09 03:00:00', '2021-11-09 05:37:37', 1353.07412069, 1362.15446184,
    1332.77800888, 1386.90097371, 0.081,
    0.6711, 5.43, 'TIME_EXIT', 2.63,
    1, '1h', '2026-03-08T18:36:22.517862'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6711,
    pnl_amount = 5.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '996C41C8BA80B0FD', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2021-11-10 17:00:00', '2021-11-11 02:37:04', 2510.65293626, 2500.16540929,
    2472.99314222, 2573.41925967, 0.0806,
    -0.4177, -3.37, 'TIME_EXIT', 9.62,
    0, '1h', '2026-03-08T18:36:22.521362'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4177,
    pnl_amount = -3.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A2079B563175884', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2021-11-10 18:00:00', '2021-11-11 05:44:02', 2842.78754316, 2856.78247287,
    2800.14573002, 2913.85723174, 0.0849,
    0.4923, 4.18, 'TIME_EXIT', 11.73,
    1, '1h', '2026-03-08T18:36:22.520316'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4923,
    pnl_amount = 4.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '117CC76783A1D3FC', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-11-14 13:00:00', '2021-11-14 21:16:47', 2794.75512135, 2814.67902596,
    2752.83379453, 2864.62399939, 0.1176,
    0.7129, 8.38, 'TIME_EXIT', 8.28,
    1, '1h', '2026-03-08T18:36:22.521864'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7129,
    pnl_amount = 8.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '69C6931FC29E910C', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-11-14 20:00:00', '2021-11-15 03:49:51', 2540.5589036, 2525.26417189,
    2578.66728716, 2477.04493101, 0.0864,
    0.602, 5.2, 'TIME_EXIT', 7.83,
    1, '1h', '2026-03-08T18:36:22.520487'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.602,
    pnl_amount = 5.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CA485A2A123B545E', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2021-11-20 13:00:00', '2021-11-20 22:17:22', 3980.34660704, 3962.07210043,
    4040.05180614, 3880.83794186, 0.1087,
    0.4591, 4.99, 'TAKE_PROFIT', 9.29,
    1, '1h', '2026-03-08T18:36:22.518009'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4591,
    pnl_amount = 4.99,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ABF90870EF5607EE', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2021-11-21 09:00:00', '2021-11-21 18:38:56', 3373.29606533, 3396.92034987,
    3322.69662435, 3457.62846696, 0.1181,
    0.7003, 8.27, 'TRAILING_STOP', 9.65,
    1, '1h', '2026-03-08T18:36:22.523136'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7003,
    pnl_amount = 8.27,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B4AA28FD36910386', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-12-02 13:00:00', '2021-12-02 23:31:12', 36045.36712498, 35908.02930294,
    35504.68661811, 36946.5013031, 0.1017,
    -0.381, -3.87, 'TIME_EXIT', 10.52,
    0, '1h', '2026-03-08T18:36:22.523037'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.381,
    pnl_amount = -3.87,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4BF8195F9FF31C69', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2021-12-05 06:00:00', '2021-12-05 15:48:36', 1397.03085177, 1403.38256014,
    1376.07538899, 1431.95662306, 0.0917,
    0.4547, 4.17, 'TAKE_PROFIT', 9.81,
    1, '1h', '2026-03-08T18:36:22.517271'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4547,
    pnl_amount = 4.17,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '301F597DE3AAD81C', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2021-12-05 17:00:00', '2021-12-06 01:52:32', 330.70897573, 328.94195188,
    335.66961036, 322.44125134, 0.0862,
    0.5343, 4.61, 'TRAILING_STOP', 8.88,
    1, '1h', '2026-03-08T18:36:22.520428'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5343,
    pnl_amount = 4.61,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '36F134AF103C4C3E', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-12-05 23:00:00', '2021-12-06 06:16:26', 419.00067753, 416.23852452,
    425.2856877, 408.52566059, 0.0973,
    0.6592, 6.41, 'TRAILING_STOP', 7.27,
    1, '1h', '2026-03-08T18:36:22.519052'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6592,
    pnl_amount = 6.41,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B85BDBD8F0A20183', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2021-12-06 00:00:00', '2021-12-06 06:58:11', 3199.01358444, 3179.99624069,
    3246.99878821, 3119.03824483, 0.0943,
    0.5945, 5.61, 'TRAILING_STOP', 6.97,
    1, '1h', '2026-03-08T18:36:22.520706'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5945,
    pnl_amount = 5.61,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '85AE8C6DDD2FCB04', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-12-17 01:00:00', '2021-12-17 10:49:14', 1723.05729756, 1730.46485869,
    1697.21143809, 1766.13373, 0.1094,
    0.4299, 4.7, 'TIME_EXIT', 9.82,
    1, '1h', '2026-03-08T18:36:22.520373'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4299,
    pnl_amount = 4.7,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '551633E1CC93720B', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-12-17 17:00:00', '2021-12-18 03:09:00', 6551.1025833, 6517.85406151,
    6649.36912205, 6387.32501872, 0.0959,
    0.5075, 4.87, 'TAKE_PROFIT', 10.15,
    1, '1h', '2026-03-08T18:36:22.517231'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5075,
    pnl_amount = 4.87,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '27A267652E7B6E9A', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2021-12-20 16:00:00', '2021-12-20 21:50:39', 796.02076506, 790.66651137,
    807.96107654, 776.12024594, 0.1104,
    0.6726, 7.43, 'TRAILING_STOP', 5.84,
    1, '1h', '2026-03-08T18:36:22.517610'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6726,
    pnl_amount = 7.43,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '39E0A836A40C8F8D', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2021-12-20 21:00:00', '2021-12-21 00:46:25', 29933.86409098, 30022.89139636,
    30382.87205235, 29185.51748871, 0.1016,
    -0.2974, -3.02, 'TIME_EXIT', 3.77,
    0, '1h', '2026-03-08T18:36:22.521282'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2974,
    pnl_amount = -3.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E2D69E20D5DBA3A4', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-12-23 22:00:00', '2021-12-24 03:21:29', 3983.52355362, 3999.27229016,
    3923.77070031, 4083.11164246, 0.1017,
    0.3953, 4.02, 'TAKE_PROFIT', 5.36,
    1, '1h', '2026-03-08T18:36:22.519862'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3953,
    pnl_amount = 4.02,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '656EB3A93018FB6A', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2021-12-24 12:00:00', '2021-12-24 19:40:01', 842.45654782, 839.57454263,
    829.8196996, 863.51796152, 0.099,
    -0.3421, -3.39, 'TIME_EXIT', 7.67,
    0, '1h', '2026-03-08T18:36:22.518553'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3421,
    pnl_amount = -3.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D07D22D336DAB0D0', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2021-12-27 01:00:00', '2021-12-27 10:34:08', 4389.75246489, 4407.6770337,
    4455.59875187, 4280.00865327, 0.1089,
    -0.4083, -4.45, 'TIME_EXIT', 9.57,
    0, '1h', '2026-03-08T18:36:22.521477'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4083,
    pnl_amount = -4.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA319BCA493B3A15', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2021-12-30 04:00:00', '2021-12-30 12:11:47', 2611.61594854, 2623.94394832,
    2572.44170932, 2676.90634726, 0.0901,
    0.472, 4.25, 'TRAILING_STOP', 8.2,
    1, '1h', '2026-03-08T18:36:22.522614'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.472,
    pnl_amount = 4.25,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A2DCC734FDC2B9EF', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2021-12-31 15:00:00', '2021-12-31 21:58:53', 12618.1213295, 12685.47878653,
    12428.84950956, 12933.57436274, 0.1007,
    0.5338, 5.37, 'TAKE_PROFIT', 6.98,
    1, '1h', '2026-03-08T18:36:22.521937'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5338,
    pnl_amount = 5.37,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1788AACBC15737B9', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-01-01 14:00:00', '2022-01-01 23:34:31', 31191.65389506, 31310.72951779,
    31659.52870348, 30411.86254768, 0.0961,
    -0.3818, -3.67, 'TIME_EXIT', 9.58,
    0, '1h', '2026-03-08T18:36:22.519275'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3818,
    pnl_amount = -3.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9903CB3F15852C45', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2022-01-02 05:00:00', '2022-01-02 07:32:57', 1115.3219132, 1122.6610793,
    1098.59208451, 1143.20496103, 0.0991,
    0.658, 6.52, 'TRAILING_STOP', 2.55,
    1, '1h', '2026-03-08T18:36:22.516996'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.658,
    pnl_amount = 6.52,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3C596342C4ADBF08', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-01-02 21:00:00', '2022-01-03 01:08:45', 946.23241968, 941.38158159,
    960.42590598, 922.57660919, 0.1127,
    0.5126, 5.78, 'TAKE_PROFIT', 4.15,
    1, '1h', '2026-03-08T18:36:22.519034'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5126,
    pnl_amount = 5.78,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '57741F5C9AEBD53A', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2022-01-03 09:00:00', '2022-01-03 19:49:50', 3446.94880242, 3426.83224124,
    3498.65303446, 3360.77508236, 0.1108,
    0.5836, 6.46, 'TAKE_PROFIT', 10.83,
    1, '1h', '2026-03-08T18:36:22.522368'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5836,
    pnl_amount = 6.46,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1768325EF7A2035F', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-01-06 15:00:00', '2022-01-06 20:35:29', 4114.3698708, 4098.72143553,
    4052.65432274, 4217.22911757, 0.1144,
    -0.3803, -4.35, 'STOP_LOSS', 5.59,
    0, '1h', '2026-03-08T18:36:22.521075'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3803,
    pnl_amount = -4.35,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BB116D5C07138D8F', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-01-07 04:00:00', '2022-01-07 07:56:27', 4266.12367741, 4281.70515809,
    4330.11553257, 4159.47058548, 0.0938,
    -0.3652, -3.43, 'TIME_EXIT', 3.94,
    0, '1h', '2026-03-08T18:36:22.520821'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3652,
    pnl_amount = -3.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E0950CEF9E80834E', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2022-01-08 21:00:00', '2022-01-09 08:17:23', 4459.5130286, 4492.01471149,
    4392.62033317, 4571.00085432, 0.0969,
    0.7288, 7.06, 'TAKE_PROFIT', 11.29,
    1, '1h', '2026-03-08T18:36:22.523100'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7288,
    pnl_amount = 7.06,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3FBC03EAE07E878D', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-01-09 17:00:00', '2022-01-09 22:17:29', 1869.77953718, 1859.24192817,
    1897.82623024, 1823.03504875, 0.0874,
    0.5636, 4.92, 'TAKE_PROFIT', 5.29,
    1, '1h', '2026-03-08T18:36:22.517843'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5636,
    pnl_amount = 4.92,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '88FC8F730353104B', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-01-13 06:00:00', '2022-01-13 08:35:49', 2105.84801796, 2097.51561329,
    2074.2602977, 2158.49421841, 0.12,
    -0.3957, -4.75, 'TIME_EXIT', 2.6,
    0, '1h', '2026-03-08T18:36:22.519257'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3957,
    pnl_amount = -4.75,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0570958D7BD2BCA7', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-01-14 08:00:00', '2022-01-14 18:37:08', 2090.84631425, 2082.30594736,
    2122.20900896, 2038.57515639, 0.1143,
    0.4085, 4.67, 'TRAILING_STOP', 10.62,
    1, '1h', '2026-03-08T18:36:22.517929'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4085,
    pnl_amount = 4.67,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3D02B251C51A5C3B', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-01-16 18:00:00', '2022-01-17 04:57:39', 21664.0159681, 21523.17434604,
    21988.97620763, 21122.4155689, 0.0932,
    0.6501, 6.06, 'TIME_EXIT', 10.96,
    1, '1h', '2026-03-08T18:36:22.520660'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6501,
    pnl_amount = 6.06,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1DA5803EA717C610', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-01-21 21:00:00', '2022-01-22 07:51:38', 843.35980409, 845.93002859,
    856.01020115, 822.27580898, 0.1187,
    -0.3048, -3.62, 'TIME_EXIT', 10.86,
    0, '1h', '2026-03-08T18:36:22.521322'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3048,
    pnl_amount = -3.62,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '386770B64D1F9860', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-01-23 22:00:00', '2022-01-24 06:19:02', 2184.34663391, 2197.02903398,
    2151.5814344, 2238.95529976, 0.0824,
    0.5806, 4.78, 'TRAILING_STOP', 8.32,
    1, '1h', '2026-03-08T18:36:22.523186'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5806,
    pnl_amount = 4.78,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CCC0B1C10C929123', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-01-28 12:00:00', '2022-01-28 15:28:34', 4465.42266673, 4443.92570413,
    4532.40400673, 4353.78710006, 0.11,
    0.4814, 5.3, 'TRAILING_STOP', 3.48,
    1, '1h', '2026-03-08T18:36:22.517473'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4814,
    pnl_amount = 5.3,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0CD74D682999421B', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2022-01-29 05:00:00', '2022-01-29 09:35:12', 4233.42155683, 4215.06270047,
    4296.92288019, 4127.58601791, 0.1042,
    0.4337, 4.52, 'TIME_EXIT', 4.59,
    1, '1h', '2026-03-08T18:36:22.519283'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4337,
    pnl_amount = 4.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8D5D8920FD1266C1', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2022-01-29 09:00:00', '2022-01-29 16:32:02', 2920.14457244, 2904.64040004,
    2963.94674103, 2847.14095813, 0.1044,
    0.5309, 5.55, 'TIME_EXIT', 7.53,
    1, '1h', '2026-03-08T18:36:22.521596'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5309,
    pnl_amount = 5.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C856644C732494F5', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-02-01 17:00:00', '2022-02-02 02:53:19', 1171.09410384, 1175.81135047,
    1153.52769228, 1200.37145644, 0.0808,
    0.4028, 3.26, 'TRAILING_STOP', 9.89,
    1, '1h', '2026-03-08T18:36:22.522019'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4028,
    pnl_amount = 3.26,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '284C124550BE2AB5', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-02-02 23:00:00', '2022-02-03 07:39:45', 14680.37597992, 14619.05411161,
    14900.58161962, 14313.36658042, 0.0925,
    0.4177, 3.86, 'TAKE_PROFIT', 8.66,
    1, '1h', '2026-03-08T18:36:22.519842'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4177,
    pnl_amount = 3.86,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1E9BAEC557589A18', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-02-05 08:00:00', '2022-02-05 19:56:57', 1588.69844256, 1583.30090861,
    1564.86796593, 1628.41590363, 0.1021,
    -0.3397, -3.47, 'TIME_EXIT', 11.95,
    0, '1h', '2026-03-08T18:36:22.521351'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3397,
    pnl_amount = -3.47,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7569ED603BF42E07', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2022-02-06 19:00:00', '2022-02-07 06:46:03', 774.59896835, 779.89605742,
    762.97998383, 793.96394256, 0.0971,
    0.6838, 6.64, 'TIME_EXIT', 11.77,
    1, '1h', '2026-03-08T18:36:22.520628'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6838,
    pnl_amount = 6.64,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0EB958C2802874F0', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-02-10 00:00:00', '2022-02-10 11:15:09', 495.56575901, 491.98347707,
    502.99924539, 483.17661503, 0.1052,
    0.7229, 7.6, 'TRAILING_STOP', 11.25,
    1, '1h', '2026-03-08T18:36:22.520812'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7229,
    pnl_amount = 7.6,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E584375F27802076', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-02-10 10:00:00', '2022-02-10 19:39:05', 3013.99550261, 3025.92321792,
    3059.20543515, 2938.64561505, 0.0891,
    -0.3957, -3.52, 'TIME_EXIT', 9.65,
    0, '1h', '2026-03-08T18:36:22.519941'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3957,
    pnl_amount = -3.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B6DEBE9EDC1E6FDD', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-02-11 00:00:00', '2022-02-11 02:21:50', 4714.71763106, 4691.89229049,
    4785.43839553, 4596.84969029, 0.1199,
    0.4841, 5.8, 'TAKE_PROFIT', 2.36,
    1, '1h', '2026-03-08T18:36:22.523154'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4841,
    pnl_amount = 5.8,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '431D158B43A8D596', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2022-02-11 22:00:00', '2022-02-12 01:22:34', 1951.6243395, 1959.71129258,
    1980.89870459, 1902.83373101, 0.0975,
    -0.4144, -4.04, 'STOP_LOSS', 3.38,
    0, '1h', '2026-03-08T18:36:22.521714'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4144,
    pnl_amount = -4.04,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B202BA3AB988F362', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-02-13 12:00:00', '2022-02-13 21:26:57', 47509.64093197, 47324.04756917,
    48222.28554595, 46321.89990867, 0.0933,
    0.3906, 3.64, 'TAKE_PROFIT', 9.45,
    1, '1h', '2026-03-08T18:36:22.520946'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3906,
    pnl_amount = 3.64,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BDFE6211B2837096', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2022-02-14 08:00:00', '2022-02-14 12:53:49', 369.69435167, 368.28367042,
    364.1489364, 378.93671046, 0.0808,
    -0.3816, -3.08, 'TIME_EXIT', 4.9,
    0, '1h', '2026-03-08T18:36:22.521178'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3816,
    pnl_amount = -3.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '90BD056E6F5EE9C2', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2022-02-22 12:00:00', '2022-02-22 19:46:44', 3357.03900662, 3339.83616073,
    3407.39459172, 3273.11303145, 0.1011,
    0.5124, 5.18, 'TRAILING_STOP', 7.78,
    1, '1h', '2026-03-08T18:36:22.522981'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5124,
    pnl_amount = 5.18,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D878A2A4ADE5C04D', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-03-01 14:00:00', '2022-03-02 01:12:43', 765.42242116, 769.29327038,
    753.94108484, 784.55798169, 0.1164,
    0.5057, 5.89, 'TIME_EXIT', 11.21,
    1, '1h', '2026-03-08T18:36:22.518262'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5057,
    pnl_amount = 5.89,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9493B0002D56D5E2', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2022-03-01 21:00:00', '2022-03-01 23:51:30', 2406.47352874, 2418.64921335,
    2370.37642581, 2466.63536695, 0.1031,
    0.506, 5.22, 'TRAILING_STOP', 2.86,
    1, '1h', '2026-03-08T18:36:22.521723'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.506,
    pnl_amount = 5.22,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0E2CCD22A2B81FF9', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2022-03-09 16:00:00', '2022-03-09 18:49:29', 4434.77405194, 4452.47189743,
    4368.25244116, 4545.64340323, 0.0863,
    0.3991, 3.44, 'TRAILING_STOP', 2.82,
    1, '1h', '2026-03-08T18:36:22.521565'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3991,
    pnl_amount = 3.44,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9A587A743485C6F8', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-03-13 06:00:00', '2022-03-13 11:24:21', 36575.70514136, 36361.02707636,
    37124.34071848, 35661.31251283, 0.0839,
    0.5869, 4.92, 'TAKE_PROFIT', 5.41,
    1, '1h', '2026-03-08T18:36:22.518166'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5869,
    pnl_amount = 4.92,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '708266722766F2C8', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-03-13 13:00:00', '2022-03-13 19:11:03', 969.33446202, 962.67567931,
    983.87447895, 945.10110047, 0.1,
    0.6869, 6.87, 'TAKE_PROFIT', 6.18,
    1, '1h', '2026-03-08T18:36:22.518972'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6869,
    pnl_amount = 6.87,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F1D5A2B23E93F24', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-03-13 19:00:00', '2022-03-13 21:37:53', 1703.55100615, 1711.49484457,
    1677.99774105, 1746.1397813, 0.1052,
    0.4663, 4.91, 'TAKE_PROFIT', 2.63,
    1, '1h', '2026-03-08T18:36:22.521503'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4663,
    pnl_amount = 4.91,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1EB5C4285944674B', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2022-03-19 00:00:00', '2022-03-19 02:54:04', 1600.43116877, 1609.75618472,
    1576.42470124, 1640.44194799, 0.0935,
    0.5827, 5.45, 'TRAILING_STOP', 2.9,
    1, '1h', '2026-03-08T18:36:22.522836'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5827,
    pnl_amount = 5.45,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '13690A9FF835E4AC', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-03-20 06:00:00', '2022-03-20 11:08:40', 3870.92210957, 3843.97884752,
    3928.98594121, 3774.14905683, 0.0896,
    0.696, 6.24, 'TIME_EXIT', 5.14,
    1, '1h', '2026-03-08T18:36:22.518752'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.696,
    pnl_amount = 6.24,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3F5A52D3817E94B9', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2022-03-21 10:00:00', '2022-03-21 12:44:59', 2654.85834827, 2643.47062372,
    2694.6812235, 2588.48688957, 0.0953,
    0.4289, 4.09, 'TRAILING_STOP', 2.75,
    1, '1h', '2026-03-08T18:36:22.519749'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4289,
    pnl_amount = 4.09,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '01D82995DE406AE1', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-03-23 17:00:00', '2022-03-23 20:07:36', 3391.80479016, 3374.1263978,
    3442.68186201, 3307.0096704, 0.094,
    0.5212, 4.9, 'TIME_EXIT', 3.13,
    1, '1h', '2026-03-08T18:36:22.517140'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5212,
    pnl_amount = 4.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BB68EA391E8CF98E', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2022-03-24 19:00:00', '2022-03-25 06:47:57', 4956.37841645, 4989.12943816,
    4882.0327402, 5080.28787686, 0.092,
    0.6608, 6.08, 'TIME_EXIT', 11.8,
    1, '1h', '2026-03-08T18:36:22.517991'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6608,
    pnl_amount = 6.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7D34DAF58D33774F', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-03-25 04:00:00', '2022-03-25 11:57:43', 4447.17150648, 4429.5305466,
    4513.87907908, 4335.99221882, 0.0991,
    0.3967, 3.93, 'TAKE_PROFIT', 7.96,
    1, '1h', '2026-03-08T18:36:22.517372'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3967,
    pnl_amount = 3.93,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3C2711CD1F61B241', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2022-04-03 20:00:00', '2022-04-04 05:18:18', 1838.0136364, 1844.71910765,
    1865.58384094, 1792.06329549, 0.0918,
    -0.3648, -3.35, 'STOP_LOSS', 9.31,
    0, '1h', '2026-03-08T18:36:22.520919'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3648,
    pnl_amount = -3.35,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '927C79D971E2D4BC', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-04-04 15:00:00', '2022-04-04 21:40:40', 3784.24207864, 3757.80561094,
    3841.00570982, 3689.63602668, 0.0833,
    0.6986, 5.82, 'TRAILING_STOP', 6.68,
    1, '1h', '2026-03-08T18:36:22.519903'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6986,
    pnl_amount = 5.82,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F917D353CCDA6846', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2022-04-05 23:00:00', '2022-04-06 09:08:38', 1234.40949826, 1230.05942419,
    1215.89335579, 1265.26973572, 0.1128,
    -0.3524, -3.97, 'STOP_LOSS', 10.14,
    0, '1h', '2026-03-08T18:36:22.522479'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3524,
    pnl_amount = -3.97,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A21CFD2A2B3A56F6', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2022-04-07 10:00:00', '2022-04-07 15:50:26', 3104.54988021, 3123.58667639,
    3057.98163201, 3182.16362721, 0.1093,
    0.6132, 6.7, 'TRAILING_STOP', 5.84,
    1, '1h', '2026-03-08T18:36:22.517290'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6132,
    pnl_amount = 6.7,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '35B425E9A4E9730F', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2022-04-15 02:00:00', '2022-04-15 12:44:22', 1934.26805556, 1942.8930817,
    1905.25403472, 1982.62475694, 0.0999,
    0.4459, 4.45, 'TAKE_PROFIT', 10.74,
    1, '1h', '2026-03-08T18:36:22.522311'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4459,
    pnl_amount = 4.45,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F6C52ED7DCDF364', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-04-19 12:00:00', '2022-04-19 20:00:24', 343.18400474, 344.59869759,
    338.03624466, 351.76360485, 0.1195,
    0.4122, 4.93, 'TIME_EXIT', 8.01,
    1, '1h', '2026-03-08T18:36:22.517491'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4122,
    pnl_amount = 4.93,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FFC0B8953F8CBE67', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2022-04-22 18:00:00', '2022-04-22 21:06:55', 4294.58339776, 4271.20370578,
    4359.00214873, 4187.21881282, 0.0856,
    0.5444, 4.66, 'TRAILING_STOP', 3.12,
    1, '1h', '2026-03-08T18:36:22.522828'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5444,
    pnl_amount = 4.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3645E16C6ECFCFA9', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-04-24 11:00:00', '2022-04-24 14:58:47', 3861.87488319, 3874.47081575,
    3919.80300644, 3765.32801111, 0.0828,
    -0.3262, -2.7, 'STOP_LOSS', 3.98,
    0, '1h', '2026-03-08T18:36:22.520650'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3262,
    pnl_amount = -2.7,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F984172ECB7329A6', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2022-04-24 21:00:00', '2022-04-25 05:07:37', 8705.86006926, 8758.26556308,
    8575.27216822, 8923.50657099, 0.1139,
    0.602, 6.86, 'TAKE_PROFIT', 8.13,
    1, '1h', '2026-03-08T18:36:22.520775'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.602,
    pnl_amount = 6.86,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3CBA7D508FC24777', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2022-04-25 19:00:00', '2022-04-25 22:50:11', 1432.22224713, 1437.92284877,
    1453.70558084, 1396.41669096, 0.1064,
    -0.398, -4.24, 'STOP_LOSS', 3.84,
    0, '1h', '2026-03-08T18:36:22.518474'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.398,
    pnl_amount = -4.24,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5BF93DC9DBF2C497', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-04-27 14:00:00', '2022-04-27 17:48:49', 3126.25498018, 3145.42808787,
    3079.36115547, 3204.41135468, 0.1034,
    0.6133, 6.34, 'TRAILING_STOP', 3.81,
    1, '1h', '2026-03-08T18:36:22.522791'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6133,
    pnl_amount = 6.34,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0592ACFC8AB4592C', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-04-30 18:00:00', '2022-05-01 03:48:53', 1691.01858649, 1703.04790363,
    1665.65330769, 1733.29405115, 0.0886,
    0.7114, 6.3, 'TIME_EXIT', 9.81,
    1, '1h', '2026-03-08T18:36:22.519978'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7114,
    pnl_amount = 6.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2ECC8E8C4CF782A9', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2022-05-04 03:00:00', '2022-05-04 07:09:03', 48341.2507555, 48629.49692742,
    47616.13199417, 49549.78202439, 0.0905,
    0.5963, 5.4, 'TAKE_PROFIT', 4.15,
    1, '1h', '2026-03-08T18:36:22.522604'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5963,
    pnl_amount = 5.4,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '47CC2B0893C3C014', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2022-05-04 08:00:00', '2022-05-04 10:47:58', 4148.95208762, 4132.01399506,
    4211.18636893, 4045.22828543, 0.1078,
    0.4082, 4.4, 'TAKE_PROFIT', 2.8,
    1, '1h', '2026-03-08T18:36:22.517075'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4082,
    pnl_amount = 4.4,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '756F6C88BBB52405', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2022-05-07 23:00:00', '2022-05-08 09:23:33', 5280.8357811, 5261.72942066,
    5201.62324439, 5412.85667563, 0.0891,
    -0.3618, -3.22, 'STOP_LOSS', 10.39,
    0, '1h', '2026-03-08T18:36:22.522755'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3618,
    pnl_amount = -3.22,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '49D4BDD19F0623F3', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-05-08 13:00:00', '2022-05-08 19:27:57', 2064.8360286, 2049.07812415,
    2095.80856903, 2013.21512789, 0.1086,
    0.7632, 8.29, 'TIME_EXIT', 6.47,
    1, '1h', '2026-03-08T18:36:22.522707'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7632,
    pnl_amount = 8.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F05450833F727036', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2022-05-08 16:00:00', '2022-05-08 19:45:30', 2038.70317302, 2051.77374693,
    2008.12262543, 2089.67075235, 0.0995,
    0.6411, 6.38, 'TAKE_PROFIT', 3.76,
    1, '1h', '2026-03-08T18:36:22.522123'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6411,
    pnl_amount = 6.38,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '89FFFA7E4B31A9D0', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-05-09 09:00:00', '2022-05-09 18:30:13', 46652.17085737, 46820.14191376,
    47351.95342023, 45485.86658593, 0.1039,
    -0.36, -3.74, 'TIME_EXIT', 9.5,
    0, '1h', '2026-03-08T18:36:22.519383'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.36,
    pnl_amount = -3.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DD0F24E91A3D09F2', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-05-10 06:00:00', '2022-05-10 16:34:28', 1380.84200075, 1388.79696665,
    1360.12937074, 1415.36305077, 0.0823,
    0.5761, 4.74, 'TRAILING_STOP', 10.57,
    1, '1h', '2026-03-08T18:36:22.521900'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5761,
    pnl_amount = 4.74,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E9C8B78FC31B6BE0', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-05-15 12:00:00', '2022-05-15 15:34:06', 1336.22936112, 1326.12481729,
    1356.27280154, 1302.82362709, 0.1164,
    0.7562, 8.8, 'TIME_EXIT', 3.57,
    1, '1h', '2026-03-08T18:36:22.516973'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7562,
    pnl_amount = 8.8,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '66A000AE8844F715', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-05-15 15:00:00', '2022-05-16 02:56:32', 105.97692284, 106.45434368,
    104.38726899, 108.62634591, 0.1186,
    0.4505, 5.34, 'TIME_EXIT', 11.94,
    1, '1h', '2026-03-08T18:36:22.522679'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4505,
    pnl_amount = 5.34,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5339396822599037', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-05-18 05:00:00', '2022-05-18 10:19:51', 46000.06363434, 46146.6310774,
    46690.06458886, 44850.06204349, 0.1076,
    -0.3186, -3.43, 'TIME_EXIT', 5.33,
    0, '1h', '2026-03-08T18:36:22.522094'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3186,
    pnl_amount = -3.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CB21495F5AB4F3AF', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-05-18 18:00:00', '2022-05-19 02:41:33', 2590.60004049, 2608.15839257,
    2551.74103988, 2655.3650415, 0.1187,
    0.6778, 8.05, 'TRAILING_STOP', 8.69,
    1, '1h', '2026-03-08T18:36:22.517700'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6778,
    pnl_amount = 8.05,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '84AF777CE0FB9AF9', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-05-23 07:00:00', '2022-05-23 16:43:18', 3036.29068268, 3045.09170952,
    3081.83504292, 2960.38341561, 0.095,
    -0.2899, -2.75, 'TIME_EXIT', 9.72,
    0, '1h', '2026-03-08T18:36:22.520326'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2899,
    pnl_amount = -2.75,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6D394D9ED7596428', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-05-23 12:00:00', '2022-05-23 23:07:52', 406.84488038, 408.1732497,
    412.94755359, 396.67375838, 0.1108,
    -0.3265, -3.62, 'TIME_EXIT', 11.13,
    0, '1h', '2026-03-08T18:36:22.521226'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3265,
    pnl_amount = -3.62,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '841B462BB9E670E2', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2022-05-30 12:00:00', '2022-05-30 22:31:02', 3102.18980129, 3092.32127056,
    3055.65695427, 3179.74454632, 0.1152,
    -0.3181, -3.67, 'STOP_LOSS', 10.52,
    0, '1h', '2026-03-08T18:36:22.522724'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3181,
    pnl_amount = -3.67,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D60005000F006815', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2022-06-01 10:00:00', '2022-06-01 16:42:21', 3057.90976102, 3042.65663404,
    3103.77840743, 2981.46201699, 0.1121,
    0.4988, 5.59, 'TRAILING_STOP', 6.71,
    1, '1h', '2026-03-08T18:36:22.516951'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4988,
    pnl_amount = 5.59,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '421B800CF36B00DC', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-06-01 13:00:00', '2022-06-01 16:38:51', 196.24057156, 194.94322192,
    199.18418013, 191.33455727, 0.0801,
    0.6611, 5.29, 'TIME_EXIT', 3.65,
    1, '1h', '2026-03-08T18:36:22.523010'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6611,
    pnl_amount = 5.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '23D5F3484D94BBD6', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-06-02 13:00:00', '2022-06-02 17:45:17', 2398.65520229, 2415.89898012,
    2362.67537426, 2458.62158235, 0.104,
    0.7189, 7.48, 'TIME_EXIT', 4.75,
    1, '1h', '2026-03-08T18:36:22.517816'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7189,
    pnl_amount = 7.48,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '31063ED0DD21FAF9', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2022-06-13 23:00:00', '2022-06-14 03:59:24', 1303.75221661, 1299.3369569,
    1284.19593336, 1336.34602202, 0.1033,
    -0.3387, -3.5, 'STOP_LOSS', 4.99,
    0, '1h', '2026-03-08T18:36:22.520157'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3387,
    pnl_amount = -3.5,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A7AEA247EDBB856A', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2022-06-15 04:00:00', '2022-06-15 12:22:23', 1337.7609967, 1342.88301731,
    1357.82741165, 1304.31697178, 0.0918,
    -0.3829, -3.52, 'TIME_EXIT', 8.37,
    0, '1h', '2026-03-08T18:36:22.522908'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3829,
    pnl_amount = -3.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '625CD92CD68303DC', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-06-18 21:00:00', '2022-06-19 05:24:32', 2172.98141058, 2186.25540483,
    2140.38668942, 2227.30594584, 0.0862,
    0.6109, 5.27, 'TRAILING_STOP', 8.41,
    1, '1h', '2026-03-08T18:36:22.517353'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6109,
    pnl_amount = 5.27,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D0968B52B5C66B0C', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2022-06-23 09:00:00', '2022-06-23 14:55:38', 4803.74281733, 4785.13950335,
    4875.79895959, 4683.6492469, 0.1085,
    0.3873, 4.2, 'TAKE_PROFIT', 5.93,
    1, '1h', '2026-03-08T18:36:22.519559'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3873,
    pnl_amount = 4.2,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A2DE944EA5EC6A4E', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2022-06-24 17:00:00', '2022-06-25 01:54:36', 4930.28112733, 4895.51057343,
    5004.23534424, 4807.02409914, 0.1081,
    0.7052, 7.62, 'TAKE_PROFIT', 8.91,
    1, '1h', '2026-03-08T18:36:22.520185'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7052,
    pnl_amount = 7.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D227C364F4E20DC9', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-07-01 22:00:00', '2022-07-02 05:38:00', 149.8541018, 148.85464494,
    152.10191333, 146.10774926, 0.1101,
    0.667, 7.34, 'TIME_EXIT', 7.63,
    1, '1h', '2026-03-08T18:36:22.520669'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.667,
    pnl_amount = 7.34,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6E7653ED16D9AE74', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-07-03 03:00:00', '2022-07-03 07:38:28', 2019.95416545, 2007.08786279,
    2050.25347793, 1969.45531131, 0.0999,
    0.637, 6.36, 'TIME_EXIT', 4.64,
    1, '1h', '2026-03-08T18:36:22.518271'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.637,
    pnl_amount = 6.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6BCF44321919C684', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2022-07-03 13:00:00', '2022-07-03 15:46:03', 31369.35568009, 31602.41331995,
    30898.81534488, 32153.58957209, 0.1122,
    0.7429, 8.33, 'TRAILING_STOP', 2.77,
    1, '1h', '2026-03-08T18:36:22.519479'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7429,
    pnl_amount = 8.33,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EEAE80FF791EBDB6', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-07-06 11:00:00', '2022-07-06 20:09:30', 967.3301109, 963.88885953,
    952.82015923, 991.51336367, 0.1114,
    -0.3557, -3.96, 'TIME_EXIT', 9.16,
    0, '1h', '2026-03-08T18:36:22.519695'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3557,
    pnl_amount = -3.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A3740DB96CA54BA8', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2022-07-08 22:00:00', '2022-07-09 02:41:46', 3134.81701426, 3156.22080673,
    3087.79475904, 3213.18743961, 0.111,
    0.6828, 7.58, 'TRAILING_STOP', 4.7,
    1, '1h', '2026-03-08T18:36:22.520241'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6828,
    pnl_amount = 7.58,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8048B614A5A04456', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2022-07-10 10:00:00', '2022-07-10 17:27:24', 3385.6630514, 3408.00296727,
    3334.87810563, 3470.30462769, 0.0988,
    0.6598, 6.52, 'TRAILING_STOP', 7.46,
    1, '1h', '2026-03-08T18:36:22.517746'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6598,
    pnl_amount = 6.52,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '92503B1AA06D58A1', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-07-11 04:00:00', '2022-07-11 10:26:44', 4409.47716681, 4387.62596875,
    4475.61932432, 4299.24023764, 0.1036,
    0.4956, 5.13, 'TIME_EXIT', 6.45,
    1, '1h', '2026-03-08T18:36:22.520401'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4956,
    pnl_amount = 5.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '151F5ED6C5E54120', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2022-07-11 20:00:00', '2022-07-11 23:36:56', 4565.86659688, 4592.23043967,
    4497.37859793, 4680.01326181, 0.1075,
    0.5774, 6.21, 'TRAILING_STOP', 3.62,
    1, '1h', '2026-03-08T18:36:22.520738'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5774,
    pnl_amount = 6.21,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B0ECE86787259DA5', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2022-07-16 16:00:00', '2022-07-16 19:08:21', 45845.02661209, 45654.26057206,
    45157.35121291, 46991.1522774, 0.0852,
    -0.4161, -3.55, 'TIME_EXIT', 3.14,
    0, '1h', '2026-03-08T18:36:22.518411'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4161,
    pnl_amount = -3.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2C64F3F949B6868D', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-07-19 08:00:00', '2022-07-19 11:14:25', 1718.99952418, 1725.62342509,
    1693.21453131, 1761.97451228, 0.113,
    0.3853, 4.36, 'TIME_EXIT', 3.24,
    1, '1h', '2026-03-08T18:36:22.518317'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3853,
    pnl_amount = 4.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A5AB3C7EB1403F6', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-07-21 14:00:00', '2022-07-21 21:24:21', 474.65820922, 471.93917218,
    481.77808236, 462.79175399, 0.1092,
    0.5728, 6.25, 'TRAILING_STOP', 7.41,
    1, '1h', '2026-03-08T18:36:22.517120'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5728,
    pnl_amount = 6.25,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '85B51CAEA5C7B32E', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2022-07-27 04:00:00', '2022-07-27 12:01:42', 4735.17928028, 4703.91212931,
    4806.20696948, 4616.79979827, 0.1198,
    0.6603, 7.91, 'TIME_EXIT', 8.03,
    1, '1h', '2026-03-08T18:36:22.521782'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6603,
    pnl_amount = 7.91,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F368D5D5089C667', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-07-30 19:00:00', '2022-07-30 22:48:41', 34702.67892983, 34502.23437821,
    35223.21911378, 33835.11195659, 0.0845,
    0.5776, 4.88, 'TRAILING_STOP', 3.81,
    1, '1h', '2026-03-08T18:36:22.517892'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5776,
    pnl_amount = 4.88,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '04028BBFF86D90E1', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-08-05 18:00:00', '2022-08-06 04:14:12', 1266.18286451, 1258.88678595,
    1285.17560747, 1234.52829289, 0.1019,
    0.5762, 5.87, 'TAKE_PROFIT', 10.24,
    1, '1h', '2026-03-08T18:36:22.520024'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5762,
    pnl_amount = 5.87,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C6AD13B39E076A9', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2022-08-07 19:00:00', '2022-08-07 23:52:11', 1740.75334182, 1735.49622442,
    1714.64204169, 1784.27217537, 0.0889,
    -0.302, -2.69, 'TIME_EXIT', 4.87,
    0, '1h', '2026-03-08T18:36:22.519488'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.302,
    pnl_amount = -2.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DF815A26A5545CF0', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-08-08 20:00:00', '2022-08-08 23:22:42', 1228.61669055, 1223.17260008,
    1247.04594091, 1197.90127329, 0.1179,
    0.4431, 5.22, 'TIME_EXIT', 3.38,
    1, '1h', '2026-03-08T18:36:22.521151'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4431,
    pnl_amount = 5.22,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DD23944391983ABB', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-08-08 21:00:00', '2022-08-09 08:25:04', 2028.66677126, 2016.43540418,
    2059.09677283, 1977.95010198, 0.1175,
    0.6029, 7.08, 'TIME_EXIT', 11.42,
    1, '1h', '2026-03-08T18:36:22.522498'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6029,
    pnl_amount = 7.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '271D0AF13AA75188', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-08-12 14:00:00', '2022-08-12 18:24:48', 758.61176502, 763.49083824,
    747.23258855, 777.57705915, 0.1199,
    0.6432, 7.71, 'TAKE_PROFIT', 4.41,
    1, '1h', '2026-03-08T18:36:22.520391'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6432,
    pnl_amount = 7.71,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '777CB91E125D58DB', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2022-08-13 15:00:00', '2022-08-13 23:59:06', 2850.22131194, 2861.21125186,
    2807.46799226, 2921.47684474, 0.0976,
    0.3856, 3.76, 'TIME_EXIT', 8.99,
    1, '1h', '2026-03-08T18:36:22.517873'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3856,
    pnl_amount = 3.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DEA718FD25551EB7', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2022-08-22 09:00:00', '2022-08-22 11:20:52', 2137.06638828, 2126.58267934,
    2169.1223841, 2083.63972857, 0.1036,
    0.4906, 5.08, 'TAKE_PROFIT', 2.35,
    1, '1h', '2026-03-08T18:36:22.518640'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4906,
    pnl_amount = 5.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '42AE8524557BB60F', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2022-08-27 06:00:00', '2022-08-27 13:34:10', 489.69971569, 486.88935748,
    497.04521142, 477.45722279, 0.1009,
    0.5739, 5.79, 'TAKE_PROFIT', 7.57,
    1, '1h', '2026-03-08T18:36:22.518668'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5739,
    pnl_amount = 5.79,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7AE837A0596FB687', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-08-29 01:00:00', '2022-08-29 04:21:51', 4750.56645521, 4782.28516951,
    4679.30795838, 4869.33061659, 0.0803,
    0.6677, 5.36, 'TAKE_PROFIT', 3.36,
    1, '1h', '2026-03-08T18:36:22.521245'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6677,
    pnl_amount = 5.36,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5F934A017430A8EB', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2022-08-29 02:00:00', '2022-08-29 09:10:56', 2698.47213963, 2717.41508394,
    2657.99505754, 2765.93394312, 0.0878,
    0.702, 6.16, 'TAKE_PROFIT', 7.18,
    1, '1h', '2026-03-08T18:36:22.518000'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.702,
    pnl_amount = 6.16,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9829E0E48606E348', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-08-29 08:00:00', '2022-08-29 16:31:25', 705.98196173, 710.00335954,
    695.3922323, 723.63151077, 0.097,
    0.5696, 5.52, 'TRAILING_STOP', 8.52,
    1, '1h', '2026-03-08T18:36:22.517527'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5696,
    pnl_amount = 5.52,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '60F0493D33FA96FD', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2022-08-29 11:00:00', '2022-08-29 18:47:47', 3608.91722445, 3628.70026654,
    3554.78346608, 3699.14015506, 0.106,
    0.5482, 5.81, 'TRAILING_STOP', 7.8,
    1, '1h', '2026-03-08T18:36:22.522800'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5482,
    pnl_amount = 5.81,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A34A43FE8A96B850', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2022-09-02 10:00:00', '2022-09-02 18:34:10', 1438.13157686, 1443.415309,
    1459.70355051, 1402.17828744, 0.1176,
    -0.3674, -4.32, 'STOP_LOSS', 8.57,
    0, '1h', '2026-03-08T18:36:22.518990'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3674,
    pnl_amount = -4.32,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DA414587BF53DC57', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2022-09-04 10:00:00', '2022-09-04 17:21:53', 427.92105252, 430.02008717,
    421.50223673, 438.61907883, 0.097,
    0.4905, 4.76, 'TRAILING_STOP', 7.36,
    1, '1h', '2026-03-08T18:36:22.520015'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4905,
    pnl_amount = 4.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '65288B0253A74B1E', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-09-04 17:00:00', '2022-09-04 20:12:48', 47428.34493587, 47165.3929369,
    48139.7701099, 46242.63631247, 0.1001,
    0.5544, 5.55, 'TIME_EXIT', 3.21,
    1, '1h', '2026-03-08T18:36:22.520148'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5544,
    pnl_amount = 5.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CCA09C9CEA4871EB', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-09-11 22:00:00', '2022-09-12 06:04:59', 580.91076147, 578.41477997,
    589.62442289, 566.38799244, 0.084,
    0.4297, 3.61, 'TAKE_PROFIT', 8.08,
    1, '1h', '2026-03-08T18:36:22.519237'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4297,
    pnl_amount = 3.61,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '26259DBB970073CA', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2022-09-12 12:00:00', '2022-09-12 16:50:26', 2144.95643983, 2151.60643435,
    2177.13078642, 2091.33252883, 0.1119,
    -0.31, -3.47, 'TIME_EXIT', 4.84,
    0, '1h', '2026-03-08T18:36:22.520214'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.31,
    pnl_amount = -3.47,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '52BEAB33B933F8EB', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-09-15 23:00:00', '2022-09-16 09:48:24', 1334.86373974, 1338.91704631,
    1354.88669584, 1301.49214625, 0.1136,
    -0.3036, -3.45, 'STOP_LOSS', 10.81,
    0, '1h', '2026-03-08T18:36:22.518824'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3036,
    pnl_amount = -3.45,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E5BDEFC7C05FDAB8', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-09-16 09:00:00', '2022-09-16 12:10:46', 3294.81905829, 3279.29270128,
    3344.24134416, 3212.44858183, 0.0953,
    0.4712, 4.49, 'TAKE_PROFIT', 3.18,
    1, '1h', '2026-03-08T18:36:22.518018'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4712,
    pnl_amount = 4.49,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '53F35C1DB7B66DDD', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2022-09-25 06:00:00', '2022-09-25 17:38:05', 477.93147984, 474.44256175,
    485.10045203, 465.98319284, 0.0975,
    0.73, 7.12, 'TAKE_PROFIT', 11.63,
    1, '1h', '2026-03-08T18:36:22.521745'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.73,
    pnl_amount = 7.12,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F57CB00B0A98ADA7', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2022-09-26 15:00:00', '2022-09-26 17:21:46', 2597.33909978, 2607.4201557,
    2558.37901328, 2662.27257727, 0.1069,
    0.3881, 4.15, 'TAKE_PROFIT', 2.36,
    1, '1h', '2026-03-08T18:36:22.519470'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3881,
    pnl_amount = 4.15,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '89B4CBD091006934', 'BB_SQUEEZE_v1', 'BNBUSDT', 'SHORT',
    '2022-09-29 05:00:00', '2022-09-29 08:34:20', 615.5686279, 612.64359815,
    624.80215732, 600.1794122, 0.1096,
    0.4752, 5.21, 'TRAILING_STOP', 3.57,
    1, '1h', '2026-03-08T18:36:22.517305'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4752,
    pnl_amount = 5.21,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F73F7EE367F40ED3', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-10-02 22:00:00', '2022-10-03 07:11:52', 34682.45275078, 34823.49351169,
    35202.68954204, 33815.39143201, 0.0902,
    -0.4067, -3.67, 'TIME_EXIT', 9.2,
    0, '1h', '2026-03-08T18:36:22.517315'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4067,
    pnl_amount = -3.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC65E2B2E137A130', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-10-06 09:00:00', '2022-10-06 17:04:17', 3180.2675992, 3190.88464595,
    3227.97161318, 3100.76090922, 0.1057,
    -0.3338, -3.53, 'STOP_LOSS', 8.07,
    0, '1h', '2026-03-08T18:36:22.518714'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3338,
    pnl_amount = -3.53,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2605EAB42A66162E', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2022-10-13 12:00:00', '2022-10-13 17:32:40', 2035.27755461, 2046.17619243,
    2004.74839129, 2086.15949347, 0.0992,
    0.5355, 5.31, 'TIME_EXIT', 5.54,
    1, '1h', '2026-03-08T18:36:22.518244'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5355,
    pnl_amount = 5.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1881DA28DE40967A', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-10-13 13:00:00', '2022-10-13 20:56:42', 2336.75235599, 2352.19315793,
    2301.70107065, 2395.17116489, 0.1044,
    0.6608, 6.9, 'TIME_EXIT', 7.95,
    1, '1h', '2026-03-08T18:36:22.521056'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6608,
    pnl_amount = 6.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '15D76D5CE253A40B', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-10-14 05:00:00', '2022-10-14 07:07:33', 3691.89890604, 3707.53786274,
    3636.52042245, 3784.1963787, 0.0803,
    0.4236, 3.4, 'TIME_EXIT', 2.13,
    1, '1h', '2026-03-08T18:36:22.520589'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4236,
    pnl_amount = 3.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E2E19FC074AAAC57', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-10-15 05:00:00', '2022-10-15 13:54:53', 2231.77716587, 2217.46506042,
    2265.25382336, 2175.98273672, 0.1011,
    0.6413, 6.48, 'TRAILING_STOP', 8.91,
    1, '1h', '2026-03-08T18:36:22.520687'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6413,
    pnl_amount = 6.48,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E9583ECF1745EF02', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-10-15 13:00:00', '2022-10-15 20:34:42', 1962.60502381, 1973.70511274,
    1933.16594846, 2011.67014941, 0.114,
    0.5656, 6.45, 'TIME_EXIT', 7.58,
    1, '1h', '2026-03-08T18:36:22.520289'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5656,
    pnl_amount = 6.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E32C20663FBC296C', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-10-18 02:00:00', '2022-10-18 05:44:32', 4100.8378768, 4126.85358,
    4039.32530865, 4203.35882372, 0.1011,
    0.6344, 6.41, 'TAKE_PROFIT', 3.74,
    1, '1h', '2026-03-08T18:36:22.523222'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6344,
    pnl_amount = 6.41,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0784A1DA0069ABEA', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-10-18 04:00:00', '2022-10-18 07:56:27', 4177.01974294, 4191.74810397,
    4239.67503909, 4072.59424937, 0.09,
    -0.3526, -3.17, 'STOP_LOSS', 3.94,
    0, '1h', '2026-03-08T18:36:22.517334'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3526,
    pnl_amount = -3.17,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C5955E28035C1758', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2022-10-21 12:00:00', '2022-10-21 21:34:55', 1711.90985982, 1703.80077583,
    1737.58850772, 1669.11211333, 0.0962,
    0.4737, 4.56, 'TAKE_PROFIT', 9.58,
    1, '1h', '2026-03-08T18:36:22.518402'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4737,
    pnl_amount = 4.56,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '01E38250DF72F506', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2022-10-24 00:00:00', '2022-10-24 02:46:01', 3187.6255856, 3171.01272361,
    3235.43996938, 3107.93494596, 0.093,
    0.5212, 4.85, 'TIME_EXIT', 2.77,
    1, '1h', '2026-03-08T18:36:22.521909'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5212,
    pnl_amount = 4.85,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '369A32841B475EDE', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2022-10-24 04:00:00', '2022-10-24 08:08:26', 26140.26753644, 26044.67700615,
    25748.16352339, 26793.77422485, 0.0982,
    -0.3657, -3.59, 'STOP_LOSS', 4.14,
    0, '1h', '2026-03-08T18:36:22.523361'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3657,
    pnl_amount = -3.59,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C532298733731160', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2022-10-27 22:00:00', '2022-10-28 05:33:22', 1321.11632957, 1328.2919597,
    1301.29958463, 1354.14423781, 0.1199,
    0.5431, 6.51, 'TRAILING_STOP', 7.56,
    1, '1h', '2026-03-08T18:36:22.519950'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5431,
    pnl_amount = 6.51,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A51A2445E0E30783', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2022-10-31 22:00:00', '2022-11-01 09:59:55', 3105.12587212, 3083.27498643,
    3151.70276021, 3027.49772532, 0.1149,
    0.7037, 8.08, 'TRAILING_STOP', 12.0,
    1, '1h', '2026-03-08T18:36:22.522359'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7037,
    pnl_amount = 8.08,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FCCFE7B3B10559A8', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-11-02 05:00:00', '2022-11-02 14:25:08', 4772.65288215, 4789.32841969,
    4844.24267538, 4653.33656009, 0.0822,
    -0.3494, -2.87, 'STOP_LOSS', 9.42,
    0, '1h', '2026-03-08T18:36:22.519704'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3494,
    pnl_amount = -2.87,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F3BE06578C9D6463', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2022-11-03 16:00:00', '2022-11-03 21:57:19', 621.17614298, 624.8901092,
    611.85850084, 636.70554656, 0.0944,
    0.5979, 5.64, 'TAKE_PROFIT', 5.96,
    1, '1h', '2026-03-08T18:36:22.520259'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5979,
    pnl_amount = 5.64,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3687568FF44AEE02', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2022-11-04 00:00:00', '2022-11-04 02:31:12', 1843.45218017, 1832.79046916,
    1871.10396287, 1797.36587566, 0.1024,
    0.5784, 5.92, 'TIME_EXIT', 2.52,
    1, '1h', '2026-03-08T18:36:22.517343'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5784,
    pnl_amount = 5.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F90D92404C22D126', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-11-04 17:00:00', '2022-11-05 02:56:24', 3528.90318543, 3539.76187243,
    3581.83673321, 3440.6806058, 0.1079,
    -0.3077, -3.32, 'STOP_LOSS', 9.94,
    0, '1h', '2026-03-08T18:36:22.521642'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3077,
    pnl_amount = -3.32,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E9D9B90D0E5EC924', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2022-11-07 03:00:00', '2022-11-07 10:27:27', 4001.76128328, 3982.60925529,
    4061.78770253, 3901.71725119, 0.0992,
    0.4786, 4.75, 'TIME_EXIT', 7.46,
    1, '1h', '2026-03-08T18:36:22.519301'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4786,
    pnl_amount = 4.75,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '262B772E6395F425', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2022-11-07 12:00:00', '2022-11-07 14:28:25', 3523.40089537, 3540.53807669,
    3470.54988194, 3611.48591775, 0.0913,
    0.4864, 4.44, 'TIME_EXIT', 2.47,
    1, '1h', '2026-03-08T18:36:22.517363'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4864,
    pnl_amount = 4.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '866EF6432BC11AE6', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2022-11-24 10:00:00', '2022-11-24 18:07:21', 1989.69125897, 1977.46203203,
    2019.53662785, 1939.94897749, 0.1026,
    0.6146, 6.31, 'TIME_EXIT', 8.12,
    1, '1h', '2026-03-08T18:36:22.519337'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6146,
    pnl_amount = 6.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '86479F3D38A19287', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2022-11-26 06:00:00', '2022-11-26 08:58:50', 2114.84860021, 2099.99209727,
    2146.57132922, 2061.97738521, 0.0951,
    0.7025, 6.68, 'TAKE_PROFIT', 2.98,
    1, '1h', '2026-03-08T18:36:22.520363'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7025,
    pnl_amount = 6.68,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FBE3D7BDA7A1D8B6', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2022-12-05 10:00:00', '2022-12-05 14:06:27', 4872.64716984, 4839.64532051,
    4945.73687739, 4750.83099059, 0.1109,
    0.6773, 7.51, 'TAKE_PROFIT', 4.11,
    1, '1h', '2026-03-08T18:36:22.523329'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6773,
    pnl_amount = 7.51,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C3D3A5A8576BAB6D', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2022-12-10 15:00:00', '2022-12-11 00:26:10', 828.83893837, 825.56594795,
    816.40635429, 849.55991183, 0.1061,
    -0.3949, -4.19, 'STOP_LOSS', 9.44,
    0, '1h', '2026-03-08T18:36:22.523388'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3949,
    pnl_amount = -4.19,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EBD4534B2498957B', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2022-12-11 07:00:00', '2022-12-11 11:01:49', 1738.04190757, 1730.77695074,
    1711.97127896, 1781.49295526, 0.1023,
    -0.418, -4.28, 'TIME_EXIT', 4.03,
    0, '1h', '2026-03-08T18:36:22.522452'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.418,
    pnl_amount = -4.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AA2FB41792088D5A', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2022-12-14 15:00:00', '2022-12-14 23:58:16', 1046.148893, 1040.53843603,
    1061.84112639, 1019.99517067, 0.1023,
    0.5363, 5.49, 'TIME_EXIT', 8.97,
    1, '1h', '2026-03-08T18:36:22.520223'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5363,
    pnl_amount = 5.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CCFFB665109ED7CC', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2022-12-27 06:00:00', '2022-12-27 14:47:36', 1161.6002577, 1167.88146629,
    1144.17625383, 1190.64026414, 0.1161,
    0.5407, 6.28, 'TRAILING_STOP', 8.79,
    1, '1h', '2026-03-08T18:36:22.517381'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5407,
    pnl_amount = 6.28,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D84077C054F89A80', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2022-12-30 20:00:00', '2022-12-30 23:02:07', 2041.76294227, 2054.0665875,
    2011.13649814, 2092.80701583, 0.12,
    0.6026, 7.23, 'TAKE_PROFIT', 3.04,
    1, '1h', '2026-03-08T18:36:22.519061'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6026,
    pnl_amount = 7.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '70D851B67ED68C10', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2022-12-31 05:00:00', '2022-12-31 16:54:58', 19411.98123764, 19322.75802517,
    19703.1609562, 18926.6817067, 0.0958,
    0.4596, 4.4, 'TIME_EXIT', 11.92,
    1, '1h', '2026-03-08T18:36:22.518531'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4596,
    pnl_amount = 4.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '94DF781E47F99B49', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-01-01 09:00:00', '2023-01-01 15:25:48', 1680.03031236, 1686.54047058,
    1705.23076704, 1638.02955455, 0.108,
    -0.3875, -4.18, 'STOP_LOSS', 6.43,
    0, '1h', '2026-03-08T18:36:22.517786'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3875,
    pnl_amount = -4.18,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5AAEC3525C245C32', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-01-02 15:00:00', '2023-01-02 19:51:28', 14271.22453019, 14185.4172184,
    14485.29289814, 13914.44391693, 0.1107,
    0.6013, 6.65, 'TRAILING_STOP', 4.86,
    1, '1h', '2026-03-08T18:36:22.517919'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6013,
    pnl_amount = 6.65,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5CF30B317555FE6E', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2023-01-05 02:00:00', '2023-01-05 10:05:54', 4877.71610955, 4856.55602058,
    4950.88185119, 4755.77320681, 0.1128,
    0.4338, 4.9, 'TAKE_PROFIT', 8.1,
    1, '1h', '2026-03-08T18:36:22.519096'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4338,
    pnl_amount = 4.9,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '33D0B83EA3BA90C1', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-01-08 01:00:00', '2023-01-08 06:52:24', 680.29462171, 682.59991718,
    690.49904104, 663.28725617, 0.0878,
    -0.3389, -2.97, 'STOP_LOSS', 5.87,
    0, '1h', '2026-03-08T18:36:22.523266'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3389,
    pnl_amount = -2.97,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F9DA60596D407B7C', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-01-10 13:00:00', '2023-01-10 21:28:48', 2191.36453825, 2185.20195518,
    2158.49407018, 2246.14865171, 0.1057,
    -0.2812, -2.97, 'STOP_LOSS', 8.48,
    0, '1h', '2026-03-08T18:36:22.520637'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2812,
    pnl_amount = -2.97,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '747AB6EC8E8B5404', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2023-01-13 02:00:00', '2023-01-13 08:02:28', 1760.78321939, 1767.50413244,
    1787.19496768, 1716.76363891, 0.1029,
    -0.3817, -3.93, 'STOP_LOSS', 6.04,
    0, '1h', '2026-03-08T18:36:22.518621'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3817,
    pnl_amount = -3.93,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8C36886994AA00AB', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-01-13 07:00:00', '2023-01-13 16:45:15', 2032.1865474, 2021.36090636,
    2062.66934561, 1981.38188372, 0.1082,
    0.5327, 5.77, 'TRAILING_STOP', 9.75,
    1, '1h', '2026-03-08T18:36:22.522084'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5327,
    pnl_amount = 5.77,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CFFFA3C385BEDAEC', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2023-01-14 08:00:00', '2023-01-14 19:09:22', 1317.29229298, 1307.84527373,
    1337.05167738, 1284.35998566, 0.0901,
    0.7172, 6.46, 'TIME_EXIT', 11.16,
    1, '1h', '2026-03-08T18:36:22.520728'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7172,
    pnl_amount = 6.46,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1BAEFD58CD974922', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-01-14 20:00:00', '2023-01-15 03:16:25', 8598.76125047, 8633.18307074,
    8727.74266922, 8383.79221921, 0.1142,
    -0.4003, -4.57, 'TIME_EXIT', 7.27,
    0, '1h', '2026-03-08T18:36:22.521372'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4003,
    pnl_amount = -4.57,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '156497D1F04B5B9C', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-01-15 03:00:00', '2023-01-15 11:10:29', 2214.90177251, 2206.45207634,
    2181.67824592, 2270.27431682, 0.1083,
    -0.3815, -4.13, 'TIME_EXIT', 8.17,
    0, '1h', '2026-03-08T18:36:22.519007'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3815,
    pnl_amount = -4.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6A1F13A460AC78F5', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-01-22 02:00:00', '2023-01-22 09:02:47', 4999.59502625, 4970.15321006,
    5074.58895165, 4874.6051506, 0.1012,
    0.5889, 5.96, 'TIME_EXIT', 7.05,
    1, '1h', '2026-03-08T18:36:22.518375'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5889,
    pnl_amount = 5.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9CDE9EE477BF3427', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2023-01-24 01:00:00', '2023-01-24 09:30:00', 1945.06202905, 1935.55893354,
    1974.23795949, 1896.43547833, 0.0894,
    0.4886, 4.37, 'TIME_EXIT', 8.5,
    1, '1h', '2026-03-08T18:36:22.520131'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4886,
    pnl_amount = 4.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9BE09BD186458467', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2023-01-26 08:00:00', '2023-01-26 14:09:06', 3143.56073304, 3128.01823339,
    3190.71414403, 3064.97171471, 0.0894,
    0.4944, 4.42, 'TRAILING_STOP', 6.15,
    1, '1h', '2026-03-08T18:36:22.522397'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4944,
    pnl_amount = 4.42,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1021CFD4BD475EF6', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2023-01-27 17:00:00', '2023-01-28 02:40:17', 4194.47601981, 4178.31226525,
    4131.55887952, 4299.33792031, 0.1069,
    -0.3854, -4.12, 'TIME_EXIT', 9.67,
    0, '1h', '2026-03-08T18:36:22.517834'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3854,
    pnl_amount = -4.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '338A920A17F07F5E', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2023-01-30 15:00:00', '2023-01-30 18:22:43', 4048.91736437, 4030.90452918,
    4109.65112484, 3947.69443026, 0.1047,
    0.4449, 4.66, 'TAKE_PROFIT', 3.38,
    1, '1h', '2026-03-08T18:36:22.521290'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4449,
    pnl_amount = 4.66,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6EDC35E7B8CD2D56', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-02-02 10:00:00', '2023-02-02 12:41:59', 1770.08710278, 1757.84148416,
    1796.63840932, 1725.83492521, 0.0944,
    0.6918, 6.53, 'TRAILING_STOP', 2.7,
    1, '1h', '2026-03-08T18:36:22.518916'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6918,
    pnl_amount = 6.53,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '76E2968C3ADCCD23', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-02-02 20:00:00', '2023-02-03 02:38:40', 4289.85671184, 4269.70358626,
    4354.20456252, 4182.61029405, 0.101,
    0.4698, 4.74, 'TRAILING_STOP', 6.64,
    1, '1h', '2026-03-08T18:36:22.518925'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4698,
    pnl_amount = 4.74,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7AEA8C2A9796A923', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-02-03 09:00:00', '2023-02-03 11:53:25', 1526.28878301, 1530.60686719,
    1549.18311476, 1488.13156344, 0.108,
    -0.2829, -3.06, 'STOP_LOSS', 2.89,
    0, '1h', '2026-03-08T18:36:22.518465'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2829,
    pnl_amount = -3.06,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3B4AEF504DD184EA', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-02-05 14:00:00', '2023-02-05 22:33:16', 42443.89260138, 42172.86101572,
    43080.5509904, 41382.79528635, 0.0933,
    0.6386, 5.96, 'TIME_EXIT', 8.55,
    1, '1h', '2026-03-08T18:36:22.518723'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6386,
    pnl_amount = 5.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0FF29BFC7D3012CB', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2023-02-05 20:00:00', '2023-02-06 05:49:38', 2303.61759236, 2288.48935411,
    2338.17185624, 2246.02715255, 0.0904,
    0.6567, 5.93, 'TIME_EXIT', 9.83,
    1, '1h', '2026-03-08T18:36:22.522716'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6567,
    pnl_amount = 5.93,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '450529C892A14BA0', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-02-09 04:00:00', '2023-02-09 06:03:08', 3196.08490759, 3206.24450494,
    3244.0261812, 3116.1827849, 0.0981,
    -0.3179, -3.12, 'STOP_LOSS', 2.05,
    0, '1h', '2026-03-08T18:36:22.520250'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3179,
    pnl_amount = -3.12,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '405217271BD7D23B', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2023-02-10 02:00:00', '2023-02-10 12:06:35', 3493.73250077, 3508.28699717,
    3441.32651326, 3581.07581329, 0.106,
    0.4166, 4.41, 'TIME_EXIT', 10.11,
    1, '1h', '2026-03-08T18:36:22.517910'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4166,
    pnl_amount = 4.41,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FFC667946145E327', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2023-02-14 10:00:00', '2023-02-14 13:24:51', 1306.86385428, 1301.60080537,
    1287.26089646, 1339.53545064, 0.1005,
    -0.4027, -4.05, 'STOP_LOSS', 3.41,
    0, '1h', '2026-03-08T18:36:22.523001'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4027,
    pnl_amount = -4.05,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2E2BBA951D4E4E0A', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-02-15 00:00:00', '2023-02-15 04:41:52', 2105.7114495, 2120.87902624,
    2074.12577775, 2158.35423573, 0.0879,
    0.7203, 6.33, 'TAKE_PROFIT', 4.7,
    1, '1h', '2026-03-08T18:36:22.519392'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7203,
    pnl_amount = 6.33,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EC2EEEC0F0464127', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-02-18 03:00:00', '2023-02-18 10:41:23', 27043.10914493, 27232.46384259,
    26637.46250775, 27719.18687355, 0.0846,
    0.7002, 5.93, 'TRAILING_STOP', 7.69,
    1, '1h', '2026-03-08T18:36:22.520006'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7002,
    pnl_amount = 5.93,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '198C37C2B4E2A639', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-02-20 15:00:00', '2023-02-20 21:06:44', 4007.3777327, 3992.88312839,
    3947.26706671, 4107.56217602, 0.1149,
    -0.3617, -4.16, 'TIME_EXIT', 6.11,
    0, '1h', '2026-03-08T18:36:22.518630'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3617,
    pnl_amount = -4.16,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DBD9525EAA82D6EB', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-03-02 15:00:00', '2023-03-03 01:32:59', 772.23867132, 767.21616765,
    783.82225139, 752.93270454, 0.0868,
    0.6504, 5.65, 'TIME_EXIT', 10.55,
    1, '1h', '2026-03-08T18:36:22.519016'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6504,
    pnl_amount = 5.65,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A82A45F758C1A834', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-03-04 04:00:00', '2023-03-04 10:35:51', 1039.99702394, 1047.16349604,
    1024.39706858, 1065.99694954, 0.0801,
    0.6891, 5.52, 'TIME_EXIT', 6.6,
    1, '1h', '2026-03-08T18:36:22.521556'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6891,
    pnl_amount = 5.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96F17C81F143CCB6', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2023-03-07 12:00:00', '2023-03-07 17:08:02', 654.40570461, 649.69492148,
    664.22179018, 638.045562, 0.0837,
    0.7199, 6.02, 'TAKE_PROFIT', 5.13,
    1, '1h', '2026-03-08T18:36:22.522388'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7199,
    pnl_amount = 6.02,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F792E1DDB94DD2A', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2023-03-09 04:00:00', '2023-03-09 14:37:39', 1099.6163881, 1095.01090863,
    1116.11063392, 1072.12597839, 0.1063,
    0.4188, 4.45, 'TAKE_PROFIT', 10.63,
    1, '1h', '2026-03-08T18:36:22.522510'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4188,
    pnl_amount = 4.45,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '76947024B855D97A', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2023-03-13 02:00:00', '2023-03-13 11:28:13', 2187.91553292, 2204.65287855,
    2155.09679992, 2242.61342124, 0.0859,
    0.765, 6.57, 'TRAILING_STOP', 9.47,
    1, '1h', '2026-03-08T18:36:22.518308'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.765,
    pnl_amount = 6.57,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9FD1852C6D1BF26C', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-03-15 11:00:00', '2023-03-15 16:08:13', 1020.59305991, 1013.05530233,
    1035.90195581, 995.07823341, 0.106,
    0.7386, 7.83, 'TAKE_PROFIT', 5.14,
    1, '1h', '2026-03-08T18:36:22.521808'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7386,
    pnl_amount = 7.83,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2DDF8E51453DD17E', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-03-15 23:00:00', '2023-03-16 10:27:09', 22510.40411348, 22367.51157784,
    22848.06017518, 21947.64401064, 0.0992,
    0.6348, 6.3, 'TIME_EXIT', 11.45,
    1, '1h', '2026-03-08T18:36:22.518562'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6348,
    pnl_amount = 6.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3BD682BD1E2B2A05', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2023-03-15 23:00:00', '2023-03-16 08:22:16', 1857.54817094, 1871.3479101,
    1829.68494837, 1903.98687521, 0.101,
    0.7429, 7.5, 'TAKE_PROFIT', 9.37,
    1, '1h', '2026-03-08T18:36:22.520839'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7429,
    pnl_amount = 7.5,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ADEC4089E38E8E02', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-03-18 05:00:00', '2023-03-18 16:41:14', 3428.60518508, 3451.04384681,
    3377.1761073, 3514.3203147, 0.105,
    0.6545, 6.87, 'TRAILING_STOP', 11.69,
    1, '1h', '2026-03-08T18:36:22.520032'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6545,
    pnl_amount = 6.87,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0BA5A71DCDE1C8D1', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2023-03-20 16:00:00', '2023-03-20 23:37:27', 3799.8815652, 3776.46225994,
    3856.87978867, 3704.88452607, 0.1167,
    0.6163, 7.19, 'TIME_EXIT', 7.62,
    1, '1h', '2026-03-08T18:36:22.518120'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6163,
    pnl_amount = 7.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9855FD7E6F93B19F', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-03-22 18:00:00', '2023-03-22 20:48:21', 2573.53603543, 2559.44518056,
    2612.13907596, 2509.19763454, 0.0861,
    0.5475, 4.71, 'TAKE_PROFIT', 2.81,
    1, '1h', '2026-03-08T18:36:22.521754'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5475,
    pnl_amount = 4.71,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F12145DA81E427AF', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2023-03-29 23:00:00', '2023-03-30 06:31:38', 3620.70331669, 3594.36506163,
    3675.01386644, 3530.18573377, 0.0856,
    0.7274, 6.23, 'TAKE_PROFIT', 7.53,
    1, '1h', '2026-03-08T18:36:22.521485'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7274,
    pnl_amount = 6.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CE5E70F1C671297A', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-03-31 19:00:00', '2023-04-01 06:09:12', 413.70051462, 410.78653915,
    419.90602234, 403.35800176, 0.1024,
    0.7044, 7.21, 'TIME_EXIT', 11.15,
    1, '1h', '2026-03-08T18:36:22.517619'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7044,
    pnl_amount = 7.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6C0EFC0FBDBA12F9', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-04-01 07:00:00', '2023-04-01 15:12:06', 4275.31568437, 4258.13087073,
    4339.44541964, 4168.43279226, 0.1169,
    0.402, 4.7, 'TAKE_PROFIT', 8.2,
    1, '1h', '2026-03-08T18:36:22.522632'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.402,
    pnl_amount = 4.7,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '404C8188781FD533', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-04-03 12:00:00', '2023-04-03 17:36:34', 4776.13580423, 4757.12389488,
    4704.49376716, 4895.53919933, 0.0844,
    -0.3981, -3.36, 'STOP_LOSS', 5.61,
    0, '1h', '2026-03-08T18:36:22.516962'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3981,
    pnl_amount = -3.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1EB8E67E0991280C', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2023-04-04 03:00:00', '2023-04-04 11:37:42', 2562.21004835, 2578.81427649,
    2523.77689763, 2626.26529956, 0.0862,
    0.648, 5.58, 'TIME_EXIT', 8.63,
    1, '1h', '2026-03-08T18:36:22.518732'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.648,
    pnl_amount = 5.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '993B466E6FDEDA29', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-04-05 07:00:00', '2023-04-05 14:28:55', 2987.70791896, 2966.4986346,
    3032.52353774, 2913.01522098, 0.0907,
    0.7099, 6.44, 'TIME_EXIT', 7.48,
    1, '1h', '2026-03-08T18:36:22.518037'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7099,
    pnl_amount = 6.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '73E0D08FF08834CF', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2023-04-06 23:00:00', '2023-04-07 01:30:03', 3199.22581628, 3218.06473957,
    3151.23742904, 3279.20646169, 0.1026,
    0.5889, 6.04, 'TIME_EXIT', 2.5,
    1, '1h', '2026-03-08T18:36:22.520866'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5889,
    pnl_amount = 6.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '22F79593F73486E5', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2023-04-07 19:00:00', '2023-04-08 06:20:41', 3830.98582778, 3857.66410884,
    3773.52104036, 3926.76047347, 0.0851,
    0.6964, 5.92, 'TAKE_PROFIT', 11.34,
    1, '1h', '2026-03-08T18:36:22.518438'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6964,
    pnl_amount = 5.92,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8BE70079B477B104', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-04-11 06:00:00', '2023-04-11 10:58:00', 4994.84141684, 5020.45809835,
    4919.91879558, 5119.71245226, 0.0878,
    0.5129, 4.5, 'TRAILING_STOP', 4.97,
    1, '1h', '2026-03-08T18:36:22.518705'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5129,
    pnl_amount = 4.5,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A1F7AEE4B70B91CC', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2023-04-11 17:00:00', '2023-04-12 00:25:05', 2847.47377347, 2859.39793273,
    2890.18588007, 2776.28692913, 0.1117,
    -0.4188, -4.68, 'STOP_LOSS', 7.42,
    0, '1h', '2026-03-08T18:36:22.518842'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4188,
    pnl_amount = -4.68,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '33C46686DCDBB190', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-04-15 03:00:00', '2023-04-15 09:48:46', 4432.97354725, 4409.59607627,
    4499.46815046, 4322.14920857, 0.1144,
    0.5274, 6.03, 'TIME_EXIT', 6.81,
    1, '1h', '2026-03-08T18:36:22.520902'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5274,
    pnl_amount = 6.03,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A04D9BF630967F32', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-04-16 08:00:00', '2023-04-16 19:59:28', 3895.66777249, 3924.96401452,
    3837.2327559, 3993.0594668, 0.1032,
    0.752, 7.76, 'TIME_EXIT', 11.99,
    1, '1h', '2026-03-08T18:36:22.518483'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.752,
    pnl_amount = 7.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EAB8593EB6D9399D', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2023-04-16 17:00:00', '2023-04-16 19:13:20', 3450.79776025, 3462.1855715,
    3502.55972666, 3364.52781625, 0.091,
    -0.33, -3.0, 'TIME_EXIT', 2.22,
    0, '1h', '2026-03-08T18:36:22.519217'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.33,
    pnl_amount = -3.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '90B80CE9A089970A', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-04-19 07:00:00', '2023-04-19 13:27:18', 35381.62535003, 35241.87128551,
    34850.90096978, 36266.16598378, 0.1008,
    -0.395, -3.98, 'STOP_LOSS', 6.46,
    0, '1h', '2026-03-08T18:36:22.521030'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.395,
    pnl_amount = -3.98,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C4DACB968F9C7415', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-04-19 20:00:00', '2023-04-20 00:39:20', 11569.63700312, 11534.89903417,
    11396.09244807, 11858.8779282, 0.0818,
    -0.3003, -2.46, 'STOP_LOSS', 4.66,
    0, '1h', '2026-03-08T18:36:22.517018'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3003,
    pnl_amount = -2.46,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC8ACBAEBD2A11DD', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-04-24 16:00:00', '2023-04-24 18:25:54', 2961.80860069, 2950.51486329,
    2917.38147168, 3035.85381571, 0.0986,
    -0.3813, -3.76, 'STOP_LOSS', 2.43,
    0, '1h', '2026-03-08T18:36:22.521160'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3813,
    pnl_amount = -3.76,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BE38BBC3791DAFEC', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-04-27 16:00:00', '2023-04-28 01:29:20', 23308.48384907, 23415.66046693,
    22958.85659134, 23891.1959453, 0.1154,
    0.4598, 5.3, 'TAKE_PROFIT', 9.49,
    1, '1h', '2026-03-08T18:36:22.518788'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4598,
    pnl_amount = 5.3,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CC6B0F3456ABD43C', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-04-29 00:00:00', '2023-04-29 02:47:30', 133.96635764, 133.49583917,
    131.95686228, 137.31551658, 0.115,
    -0.3512, -4.04, 'STOP_LOSS', 2.79,
    0, '1h', '2026-03-08T18:36:22.521048'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3512,
    pnl_amount = -4.04,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B00D7E8968E47C70', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-04-30 10:00:00', '2023-04-30 15:16:55', 405.03307737, 403.68979057,
    398.95758121, 415.1589043, 0.1133,
    -0.3316, -3.76, 'STOP_LOSS', 5.28,
    0, '1h', '2026-03-08T18:36:22.521094'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3316,
    pnl_amount = -3.76,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E64C44FF0DEECB7D', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-05-03 15:00:00', '2023-05-03 19:16:36', 3652.76763762, 3625.4975859,
    3707.55915218, 3561.44844668, 0.1041,
    0.7466, 7.77, 'TRAILING_STOP', 4.28,
    1, '1h', '2026-03-08T18:36:22.522470'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7466,
    pnl_amount = 7.77,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '74E04328B573974B', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2023-05-03 17:00:00', '2023-05-03 22:36:20', 3932.87969312, 3917.70786647,
    3873.88649773, 4031.20168545, 0.1075,
    -0.3858, -4.15, 'STOP_LOSS', 5.61,
    0, '1h', '2026-03-08T18:36:22.521882'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3858,
    pnl_amount = -4.15,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FC81E50596D876BA', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-05-04 13:00:00', '2023-05-04 23:09:57', 48389.73727711, 48626.65680865,
    47663.89121795, 49599.48070903, 0.1022,
    0.4896, 5.0, 'TAKE_PROFIT', 10.17,
    1, '1h', '2026-03-08T18:36:22.522549'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4896,
    pnl_amount = 5.0,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E3C41991412FE6E6', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2023-05-06 14:00:00', '2023-05-06 18:41:34', 2997.49379894, 3012.43145382,
    2952.53139195, 3072.43114391, 0.0839,
    0.4983, 4.18, 'TAKE_PROFIT', 4.69,
    1, '1h', '2026-03-08T18:36:22.517949'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4983,
    pnl_amount = 4.18,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9361AF9F7ED2693A', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2023-05-08 01:00:00', '2023-05-08 12:52:21', 3069.5929595, 3057.70254706,
    3023.54906511, 3146.33278348, 0.1082,
    -0.3874, -4.19, 'TIME_EXIT', 11.87,
    0, '1h', '2026-03-08T18:36:22.520336'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3874,
    pnl_amount = -4.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7788309BE92556A4', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2023-05-09 07:00:00', '2023-05-09 14:17:30', 2339.21429708, 2327.64754371,
    2374.30251154, 2280.73393966, 0.0979,
    0.4945, 4.84, 'TIME_EXIT', 7.29,
    1, '1h', '2026-03-08T18:36:22.517882'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4945,
    pnl_amount = 4.84,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98C8F95CB522A1F1', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-05-12 13:00:00', '2023-05-12 23:34:26', 38047.46962091, 37846.22030547,
    38618.18166523, 37096.28288039, 0.0872,
    0.5289, 4.61, 'TIME_EXIT', 10.57,
    1, '1h', '2026-03-08T18:36:22.521198'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5289,
    pnl_amount = 4.61,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '71D93E833CBA4E02', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2023-05-13 12:00:00', '2023-05-13 23:35:25', 994.44625562, 990.45264702,
    979.52956179, 1019.30741201, 0.0827,
    -0.4016, -3.32, 'STOP_LOSS', 11.59,
    0, '1h', '2026-03-08T18:36:22.522592'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4016,
    pnl_amount = -3.32,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '964973612C8824EC', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-05-14 01:00:00', '2023-05-14 05:03:01', 174.41990162, 173.71327193,
    177.03620014, 170.05940408, 0.0894,
    0.4051, 3.62, 'TAKE_PROFIT', 4.05,
    1, '1h', '2026-03-08T18:36:22.519043'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4051,
    pnl_amount = 3.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '069FE4E95EB59092', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-05-22 00:00:00', '2023-05-22 10:22:41', 27468.1527142, 27674.70245936,
    27056.13042349, 28154.85653206, 0.0891,
    0.752, 6.7, 'TAKE_PROFIT', 10.38,
    1, '1h', '2026-03-08T18:36:22.519988'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.752,
    pnl_amount = 6.7,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EAF48ABAA4EC3837', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2023-05-23 05:00:00', '2023-05-23 11:43:44', 1966.29518821, 1973.96573292,
    1936.80076039, 2015.45256792, 0.0999,
    0.3901, 3.9, 'TAKE_PROFIT', 6.73,
    1, '1h', '2026-03-08T18:36:22.517455'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3901,
    pnl_amount = 3.9,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '922AA2B62AC27205', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-05-24 16:00:00', '2023-05-24 18:44:33', 21760.2408804, 21821.38886835,
    22086.6444936, 21216.23485839, 0.081,
    -0.281, -2.28, 'TIME_EXIT', 2.74,
    0, '1h', '2026-03-08T18:36:22.517718'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.281,
    pnl_amount = -2.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8BFAD4769EA2DF19', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-05-26 00:00:00', '2023-05-26 03:00:50', 14432.97807308, 14347.2840749,
    14649.47274417, 14072.15362125, 0.1104,
    0.5937, 6.55, 'TAKE_PROFIT', 3.01,
    1, '1h', '2026-03-08T18:36:22.519625'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5937,
    pnl_amount = 6.55,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '894D5C35AD025636', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-05-27 23:00:00', '2023-05-28 10:45:08', 11011.74461669, 11079.51184317,
    10846.56844744, 11287.03823211, 0.0934,
    0.6154, 5.75, 'TAKE_PROFIT', 11.75,
    1, '1h', '2026-03-08T18:36:22.522819'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6154,
    pnl_amount = 5.75,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A2B5CF4B41BCD810', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2023-05-29 12:00:00', '2023-05-29 14:57:49', 1305.25475061, 1299.04059735,
    1324.83357187, 1272.62338185, 0.1024,
    0.4761, 4.87, 'TIME_EXIT', 2.96,
    1, '1h', '2026-03-08T18:36:22.519355'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4761,
    pnl_amount = 4.87,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '183C58AB7A3C2294', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2023-06-03 22:00:00', '2023-06-04 02:35:03', 17.18488737, 17.29433577,
    16.92711406, 17.61450956, 0.1084,
    0.6369, 6.91, 'TAKE_PROFIT', 4.58,
    1, '1h', '2026-03-08T18:36:22.518779'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6369,
    pnl_amount = 6.91,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '972CA93BB95AB5FC', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2023-06-13 02:00:00', '2023-06-13 11:20:23', 3819.94913633, 3807.62214022,
    3762.64989928, 3915.44786474, 0.0928,
    -0.3227, -3.0, 'TIME_EXIT', 9.34,
    0, '1h', '2026-03-08T18:36:22.518833'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3227,
    pnl_amount = -3.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '943CA6A855225978', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2023-06-14 06:00:00', '2023-06-14 14:47:53', 4534.63121213, 4560.08457223,
    4466.61174394, 4647.99699243, 0.0971,
    0.5613, 5.45, 'TRAILING_STOP', 8.8,
    1, '1h', '2026-03-08T18:36:22.523046'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5613,
    pnl_amount = 5.45,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BE37F87A51DFE35C', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2023-06-14 23:00:00', '2023-06-15 05:19:42', 3229.40884728, 3207.48904553,
    3277.84997999, 3148.6736261, 0.0859,
    0.6788, 5.83, 'TRAILING_STOP', 6.33,
    1, '1h', '2026-03-08T18:36:22.520306'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6788,
    pnl_amount = 5.83,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CB8FC43F4093D7A8', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-06-16 04:00:00', '2023-06-16 06:40:37', 21792.05482877, 21728.06289452,
    21465.17400634, 22336.85619949, 0.1061,
    -0.2936, -3.12, 'TIME_EXIT', 2.68,
    0, '1h', '2026-03-08T18:36:22.520884'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2936,
    pnl_amount = -3.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9C55EDFE7E6BDF85', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-06-16 17:00:00', '2023-06-17 03:57:01', 570.95611077, 574.35657813,
    562.3917691, 585.23001354, 0.1142,
    0.5956, 6.8, 'TAKE_PROFIT', 10.95,
    1, '1h', '2026-03-08T18:36:22.520803'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5956,
    pnl_amount = 6.8,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9550983A652E02D0', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2023-07-01 19:00:00', '2023-07-02 04:58:14', 936.40535257, 939.58159731,
    950.45143286, 912.99521876, 0.0801,
    -0.3392, -2.72, 'STOP_LOSS', 9.97,
    0, '1h', '2026-03-08T18:36:22.521254'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3392,
    pnl_amount = -2.72,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A3F64199DDCAEE8', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-07-06 16:00:00', '2023-07-07 03:13:13', 1047.75392952, 1042.09996197,
    1063.47023847, 1021.56008129, 0.0968,
    0.5396, 5.22, 'TIME_EXIT', 11.22,
    1, '1h', '2026-03-08T18:36:22.518907'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5396,
    pnl_amount = 5.22,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD4E325A55EFB0D5', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-07-06 18:00:00', '2023-07-06 21:13:05', 4794.71509662, 4780.12890023,
    4722.79437017, 4914.58297403, 0.0801,
    -0.3042, -2.44, 'TIME_EXIT', 3.22,
    0, '1h', '2026-03-08T18:36:22.518084'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3042,
    pnl_amount = -2.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A1CE8153764774C2', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-07-07 17:00:00', '2023-07-08 02:18:09', 2015.71093906, 2008.32385539,
    1985.47527497, 2066.10371253, 0.1187,
    -0.3665, -4.35, 'TIME_EXIT', 9.3,
    0, '1h', '2026-03-08T18:36:22.518235'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3665,
    pnl_amount = -4.35,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CF7A5FD0D866B458', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-07-08 12:00:00', '2023-07-08 22:50:31', 21071.33033112, 20986.33794097,
    21387.40028609, 20544.54707284, 0.109,
    0.4034, 4.4, 'TIME_EXIT', 10.84,
    1, '1h', '2026-03-08T18:36:22.520122'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4034,
    pnl_amount = 4.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '992B18C09165105A', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-07-11 14:00:00', '2023-07-11 22:40:20', 1612.38848297, 1606.74987285,
    1588.20265572, 1652.69819504, 0.117,
    -0.3497, -4.09, 'TIME_EXIT', 8.67,
    0, '1h', '2026-03-08T18:36:22.523249'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3497,
    pnl_amount = -4.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7EE2B8F82F07A877', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2023-07-11 18:00:00', '2023-07-11 20:23:01', 2380.40532504, 2371.75697975,
    2344.69924517, 2439.91545817, 0.1039,
    -0.3633, -3.78, 'TIME_EXIT', 2.38,
    0, '1h', '2026-03-08T18:36:22.519785'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3633,
    pnl_amount = -3.78,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B83A5346707EC26E', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2023-07-13 03:00:00', '2023-07-13 06:29:18', 2636.76374756, 2629.30229573,
    2597.21229135, 2702.68284125, 0.1081,
    -0.283, -3.06, 'STOP_LOSS', 3.49,
    0, '1h', '2026-03-08T18:36:22.520757'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.283,
    pnl_amount = -3.06,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E18E7535FB98EC71', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2023-07-13 20:00:00', '2023-07-14 06:32:36', 4276.6194273, 4299.88796839,
    4212.47013589, 4383.53491298, 0.1163,
    0.5441, 6.33, 'TIME_EXIT', 10.54,
    1, '1h', '2026-03-08T18:36:22.518879'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5441,
    pnl_amount = 6.33,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2BF3EADB243C66B6', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-07-18 05:00:00', '2023-07-18 13:19:43', 281.45441861, 282.67332963,
    277.23260233, 288.49077907, 0.1009,
    0.4331, 4.37, 'TIME_EXIT', 8.33,
    1, '1h', '2026-03-08T18:36:22.522265'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4331,
    pnl_amount = 4.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8DB153B48CB854C3', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2023-07-28 11:00:00', '2023-07-28 16:21:38', 3460.46157817, 3446.78848989,
    3512.36850184, 3373.95003871, 0.0838,
    0.3951, 3.31, 'TIME_EXIT', 5.36,
    1, '1h', '2026-03-08T18:36:22.520981'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3951,
    pnl_amount = 3.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '50E5FAA49A785A41', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-08-01 11:00:00', '2023-08-01 14:53:04', 22186.83249275, 22085.00520498,
    22519.63498014, 21632.16168043, 0.1185,
    0.459, 5.44, 'TRAILING_STOP', 3.88,
    1, '1h', '2026-03-08T18:36:22.521512'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.459,
    pnl_amount = 5.44,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A8B9BC9DD2B72C99', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2023-08-03 20:00:00', '2023-08-04 02:12:21', 2803.60169085, 2816.12703346,
    2761.54766549, 2873.69173312, 0.1038,
    0.4468, 4.64, 'TIME_EXIT', 6.21,
    1, '1h', '2026-03-08T18:36:22.522203'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4468,
    pnl_amount = 4.64,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3EE57E16A7A7769A', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-08-07 17:00:00', '2023-08-08 04:12:44', 41207.39350223, 41035.02369762,
    40589.28259969, 42237.57833978, 0.1067,
    -0.4183, -4.46, 'STOP_LOSS', 11.21,
    0, '1h', '2026-03-08T18:36:22.521660'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4183,
    pnl_amount = -4.46,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '89F202CA0BEBE838', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-08-13 02:00:00', '2023-08-13 06:14:35', 2664.75008685, 2651.92842059,
    2704.72133815, 2598.13133468, 0.1135,
    0.4812, 5.46, 'TAKE_PROFIT', 4.24,
    1, '1h', '2026-03-08T18:36:22.521530'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4812,
    pnl_amount = 5.46,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CDC2206CA3DE02BE', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-08-15 15:00:00', '2023-08-15 22:39:05', 36714.20366839, 36534.94921601,
    37264.91672342, 35796.34857668, 0.1042,
    0.4882, 5.09, 'TRAILING_STOP', 7.65,
    1, '1h', '2026-03-08T18:36:22.522662'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4882,
    pnl_amount = 5.09,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '65BD60B00593AB27', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2023-08-16 04:00:00', '2023-08-16 13:32:36', 932.45764965, 938.81981537,
    918.4707849, 955.76909089, 0.0938,
    0.6823, 6.4, 'TAKE_PROFIT', 9.54,
    1, '1h', '2026-03-08T18:36:22.517774'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6823,
    pnl_amount = 6.4,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DA48FBBE2D71C4D5', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2023-08-18 00:00:00', '2023-08-18 07:38:01', 4423.07557227, 4456.50557806,
    4356.72943868, 4533.65246157, 0.1073,
    0.7558, 8.11, 'TAKE_PROFIT', 7.63,
    1, '1h', '2026-03-08T18:36:22.521963'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7558,
    pnl_amount = 8.11,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '759E75706C2BB86C', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-08-21 04:00:00', '2023-08-21 06:12:55', 646.73116011, 649.03740971,
    656.43212751, 630.56288111, 0.0927,
    -0.3566, -3.31, 'STOP_LOSS', 2.22,
    0, '1h', '2026-03-08T18:36:22.519079'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3566,
    pnl_amount = -3.31,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '87888DCF4A4E4C9E', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-08-23 15:00:00', '2023-08-23 21:53:15', 3878.4623682, 3904.74565622,
    3820.28543267, 3975.4239274, 0.1052,
    0.6777, 7.13, 'TIME_EXIT', 6.89,
    1, '1h', '2026-03-08T18:36:22.520766'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6777,
    pnl_amount = 7.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7E8C6EAF54A325F6', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-08-26 11:00:00', '2023-08-26 16:36:19', 39450.79433998, 39606.26688529,
    38859.03242488, 40437.06419848, 0.0938,
    0.3941, 3.7, 'TRAILING_STOP', 5.61,
    1, '1h', '2026-03-08T18:36:22.522114'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3941,
    pnl_amount = 3.7,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '072BD31C449BB060', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2023-08-29 14:00:00', '2023-08-30 01:07:39', 4366.58632838, 4349.56417712,
    4301.08753346, 4475.75098659, 0.0817,
    -0.3898, -3.18, 'STOP_LOSS', 11.13,
    0, '1h', '2026-03-08T18:36:22.520298'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3898,
    pnl_amount = -3.18,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0CD3AA391975215A', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2023-08-31 05:00:00', '2023-08-31 12:35:46', 3932.86407042, 3945.33649584,
    3991.85703147, 3834.54246866, 0.0837,
    -0.3171, -2.65, 'STOP_LOSS', 7.6,
    0, '1h', '2026-03-08T18:36:22.522347'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3171,
    pnl_amount = -2.65,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F83874FD70D7235A', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-08-31 16:00:00', '2023-08-31 20:19:39', 4010.4855282, 3997.47460248,
    3950.32824528, 4110.74766641, 0.0829,
    -0.3244, -2.69, 'STOP_LOSS', 4.33,
    0, '1h', '2026-03-08T18:36:22.522670'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3244,
    pnl_amount = -2.69,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7FD437072C31CA7D', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-09-03 17:00:00', '2023-09-04 02:54:57', 3164.20634948, 3145.77747735,
    3211.66944472, 3085.10119074, 0.1135,
    0.5824, 6.61, 'TAKE_PROFIT', 9.92,
    1, '1h', '2026-03-08T18:36:22.519197'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5824,
    pnl_amount = 6.61,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9B9A0F4908FE4DC1', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-09-03 18:00:00', '2023-09-04 02:40:16', 2380.85733395, 2390.12180328,
    2345.14447394, 2440.3787673, 0.0926,
    0.3891, 3.6, 'TIME_EXIT', 8.67,
    1, '1h', '2026-03-08T18:36:22.517736'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3891,
    pnl_amount = 3.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '52FBE3F3BC118083', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-09-04 00:00:00', '2023-09-04 03:43:03', 3204.29639373, 3189.71633098,
    3252.36083963, 3124.18898388, 0.1156,
    0.455, 5.26, 'TIME_EXIT', 3.72,
    1, '1h', '2026-03-08T18:36:22.520794'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.455,
    pnl_amount = 5.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BACB9520B237462D', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2023-09-05 07:00:00', '2023-09-05 14:13:11', 855.46533441, 861.57964746,
    842.6333544, 876.85196777, 0.0991,
    0.7147, 7.09, 'TRAILING_STOP', 7.22,
    1, '1h', '2026-03-08T18:36:22.517970'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7147,
    pnl_amount = 7.09,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B9599FFABFC691ED', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-09-06 03:00:00', '2023-09-06 09:25:35', 3897.85744073, 3919.37881573,
    3839.38957912, 3995.30387675, 0.085,
    0.5521, 4.69, 'TIME_EXIT', 6.43,
    1, '1h', '2026-03-08T18:36:22.517464'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5521,
    pnl_amount = 4.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A9F407A93DD28E7D', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-09-07 03:00:00', '2023-09-07 08:19:40', 47989.64454495, 48358.35482266,
    47269.79987677, 49189.38565857, 0.1029,
    0.7683, 7.91, 'TRAILING_STOP', 5.33,
    1, '1h', '2026-03-08T18:36:22.519225'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7683,
    pnl_amount = 7.91,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DCF2F27F2409705C', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-09-07 05:00:00', '2023-09-07 08:53:47', 184.63096024, 185.21255595,
    187.40042464, 180.01518623, 0.1027,
    -0.315, -3.24, 'STOP_LOSS', 3.9,
    0, '1h', '2026-03-08T18:36:22.522246'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.315,
    pnl_amount = -3.24,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8E76E6AA7F0CE53E', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-09-08 09:00:00', '2023-09-08 20:20:56', 48766.42566163, 48392.31608594,
    49497.92204656, 47547.26502009, 0.0889,
    0.7671, 6.82, 'TRAILING_STOP', 11.35,
    1, '1h', '2026-03-08T18:36:22.522103'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7671,
    pnl_amount = 6.82,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA89C896842F7AF6', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2023-09-14 06:00:00', '2023-09-14 08:46:59', 3611.50355884, 3636.51475114,
    3557.33100546, 3701.79114781, 0.1003,
    0.6925, 6.94, 'TIME_EXIT', 2.78,
    1, '1h', '2026-03-08T18:36:22.517653'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6925,
    pnl_amount = 6.94,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BBA802B439741945', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2023-09-21 11:00:00', '2023-09-21 15:42:38', 3160.01113096, 3146.67884965,
    3207.41129792, 3081.01085268, 0.1155,
    0.4219, 4.87, 'TIME_EXIT', 4.71,
    1, '1h', '2026-03-08T18:36:22.518216'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4219,
    pnl_amount = 4.87,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '62F66935B9179F52', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2023-10-01 16:00:00', '2023-10-01 21:45:41', 3431.91791668, 3421.21002846,
    3380.43914793, 3517.71586459, 0.0824,
    -0.312, -2.57, 'STOP_LOSS', 5.76,
    0, '1h', '2026-03-08T18:36:22.522558'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.312,
    pnl_amount = -2.57,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B7F020283B37726B', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2023-10-03 17:00:00', '2023-10-04 00:35:55', 1120.02837839, 1111.59994645,
    1136.82880407, 1092.02766893, 0.0853,
    0.7525, 6.42, 'TRAILING_STOP', 7.6,
    1, '1h', '2026-03-08T18:36:22.521459'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7525,
    pnl_amount = 6.42,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D6CF0D349A76AC9E', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-10-05 02:00:00', '2023-10-05 13:36:40', 3285.32089086, 3271.4314151,
    3334.60070423, 3203.18786859, 0.0949,
    0.4228, 4.01, 'TAKE_PROFIT', 11.61,
    1, '1h', '2026-03-08T18:36:22.520104'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4228,
    pnl_amount = 4.01,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '36E88EC65C935C3E', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-10-06 08:00:00', '2023-10-06 14:53:41', 526.18231637, 524.61680267,
    518.28958162, 539.33687428, 0.0949,
    -0.2975, -2.82, 'TIME_EXIT', 6.89,
    0, '1h', '2026-03-08T18:36:22.520446'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2975,
    pnl_amount = -2.82,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4D2E54919CE2472A', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-10-06 11:00:00', '2023-10-06 21:51:50', 2917.84819787, 2938.27463767,
    2874.0804749, 2990.79440282, 0.0916,
    0.7001, 6.41, 'TRAILING_STOP', 10.86,
    1, '1h', '2026-03-08T18:36:22.522038'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7001,
    pnl_amount = 6.41,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '21684099FBCD3CA7', 'BB_SQUEEZE_v1', 'BNBUSDT', 'LONG',
    '2023-10-11 13:00:00', '2023-10-11 21:36:28', 1250.20646534, 1256.00068168,
    1231.45336836, 1281.46162697, 0.0878,
    0.4635, 4.07, 'TRAILING_STOP', 8.61,
    1, '1h', '2026-03-08T18:36:22.523240'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4635,
    pnl_amount = 4.07,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6131367C545C5F13', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2023-10-23 09:00:00', '2023-10-23 20:08:36', 731.64620348, 736.56594751,
    720.67151043, 749.93735857, 0.12,
    0.6724, 8.07, 'TRAILING_STOP', 11.14,
    1, '1h', '2026-03-08T18:36:22.521633'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6724,
    pnl_amount = 8.07,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8D3987F9FE4A75FF', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2023-10-28 14:00:00', '2023-10-28 17:21:31', 39856.74872406, 39727.94960529,
    39258.8974932, 40853.16744216, 0.1048,
    -0.3232, -3.39, 'TIME_EXIT', 3.36,
    0, '1h', '2026-03-08T18:36:22.520696'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3232,
    pnl_amount = -3.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D000EFD456ED195B', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2023-11-05 23:00:00', '2023-11-06 05:53:06', 1517.80391621, 1513.35595561,
    1495.03685746, 1555.74901411, 0.0869,
    -0.2931, -2.55, 'TIME_EXIT', 6.89,
    0, '1h', '2026-03-08T18:36:22.519450'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2931,
    pnl_amount = -2.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0D122B9151B2B53D', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2023-11-07 14:00:00', '2023-11-07 22:44:06', 4244.22737829, 4225.0850068,
    4307.89078896, 4138.12169383, 0.0831,
    0.451, 3.75, 'TAKE_PROFIT', 8.74,
    1, '1h', '2026-03-08T18:36:22.520496'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.451,
    pnl_amount = 3.75,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D64A08634BA2F652', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2023-11-07 18:00:00', '2023-11-07 22:30:29', 1001.28568793, 998.23833172,
    986.26640261, 1026.31783013, 0.1,
    -0.3043, -3.04, 'STOP_LOSS', 4.51,
    0, '1h', '2026-03-08T18:36:22.521428'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3043,
    pnl_amount = -3.04,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8E2C8597E82D61AF', 'BB_SQUEEZE_v1', 'BNBUSDT', 'LONG',
    '2023-11-09 11:00:00', '2023-11-09 18:14:58', 3400.39903605, 3418.71868967,
    3349.39305051, 3485.40901195, 0.0904,
    0.5388, 4.87, 'TIME_EXIT', 7.25,
    1, '1h', '2026-03-08T18:36:22.519550'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5388,
    pnl_amount = 4.87,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0D13E36242AA6056', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-11-09 23:00:00', '2023-11-10 08:03:55', 9964.72596435, 9900.31600395,
    10114.19685381, 9715.60781524, 0.1074,
    0.6464, 6.94, 'TRAILING_STOP', 9.07,
    1, '1h', '2026-03-08T18:36:22.519616'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6464,
    pnl_amount = 6.94,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9BD4B30C7AEF635A', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-11-12 17:00:00', '2023-11-13 03:31:31', 22400.83290858, 22292.03324848,
    22736.84540221, 21840.81208586, 0.1077,
    0.4857, 5.23, 'TAKE_PROFIT', 10.53,
    1, '1h', '2026-03-08T18:36:22.520086'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4857,
    pnl_amount = 5.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A4BCF553D57D451', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-11-18 09:00:00', '2023-11-18 19:02:56', 329.98553298, 328.44904274,
    334.93531598, 321.73589466, 0.0852,
    0.4656, 3.97, 'TIME_EXIT', 10.05,
    1, '1h', '2026-03-08T18:36:22.517189'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4656,
    pnl_amount = 3.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3069F64E45D64404', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-11-18 10:00:00', '2023-11-18 14:48:12', 3592.61215883, 3606.62058874,
    3538.72297644, 3682.4274628, 0.0848,
    0.3899, 3.3, 'TIME_EXIT', 4.8,
    1, '1h', '2026-03-08T18:36:22.523177'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3899,
    pnl_amount = 3.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0EE8F1899F785D36', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-11-20 06:00:00', '2023-11-20 14:41:36', 1612.70209454, 1622.85769977,
    1588.51156312, 1653.0196469, 0.0971,
    0.6297, 6.11, 'TIME_EXIT', 8.69,
    1, '1h', '2026-03-08T18:36:22.519731'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6297,
    pnl_amount = 6.11,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E62108CF1A8E804E', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-11-22 17:00:00', '2023-11-23 00:57:34', 2548.2539354, 2533.15814811,
    2586.47774443, 2484.54758702, 0.1132,
    0.5924, 6.71, 'TAKE_PROFIT', 7.96,
    1, '1h', '2026-03-08T18:36:22.519823'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5924,
    pnl_amount = 6.71,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CEEA081006BC5394', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-11-26 11:00:00', '2023-11-26 19:29:53', 2321.57927396, 2310.26398573,
    2356.40296306, 2263.53979211, 0.0991,
    0.4874, 4.83, 'TAKE_PROFIT', 8.5,
    1, '1h', '2026-03-08T18:36:22.520524'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4874,
    pnl_amount = 4.83,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2E40B4B5592AC3C6', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2023-11-27 06:00:00', '2023-11-27 10:49:02', 4761.83040879, 4795.81740601,
    4690.40295266, 4880.87616901, 0.091,
    0.7137, 6.49, 'TAKE_PROFIT', 4.82,
    1, '1h', '2026-03-08T18:36:22.518861'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7137,
    pnl_amount = 6.49,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F867C0B7B1A0913', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2023-11-28 11:00:00', '2023-11-28 14:16:08', 1537.72610851, 1531.96005565,
    1514.66021689, 1576.16926123, 0.1123,
    -0.375, -4.21, 'STOP_LOSS', 3.27,
    0, '1h', '2026-03-08T18:36:22.519652'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.375,
    pnl_amount = -4.21,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '033EB54E119C7818', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-11-29 11:00:00', '2023-11-29 20:58:23', 2706.6670068, 2717.64369237,
    2747.2670119, 2639.00033163, 0.0944,
    -0.4055, -3.83, 'TIME_EXIT', 9.97,
    0, '1h', '2026-03-08T18:36:22.519247'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4055,
    pnl_amount = -3.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FDA7B898661264F9', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-11-29 16:00:00', '2023-11-29 18:19:09', 4304.70555365, 4286.34317821,
    4369.27613695, 4197.08791481, 0.1141,
    0.4266, 4.87, 'TRAILING_STOP', 2.32,
    1, '1h', '2026-03-08T18:36:22.518570'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4266,
    pnl_amount = 4.87,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '398C01FD705E705B', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2023-12-01 07:00:00', '2023-12-01 18:36:48', 2455.78382235, 2441.99091724,
    2492.62057969, 2394.38922679, 0.0867,
    0.5616, 4.87, 'TRAILING_STOP', 11.61,
    1, '1h', '2026-03-08T18:36:22.521873'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5616,
    pnl_amount = 4.87,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B0174B5BE557A9AD', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-12-01 07:00:00', '2023-12-01 09:56:36', 385.2837778, 384.09966546,
    379.50452114, 394.91587225, 0.1025,
    -0.3073, -3.15, 'TIME_EXIT', 2.94,
    0, '1h', '2026-03-08T18:36:22.522217'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3073,
    pnl_amount = -3.15,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B0F5F241739A6977', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-12-02 06:00:00', '2023-12-02 16:12:03', 1268.74981312, 1264.82959247,
    1249.71856593, 1300.46855845, 0.0945,
    -0.309, -2.92, 'STOP_LOSS', 10.2,
    0, '1h', '2026-03-08T18:36:22.522228'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.309,
    pnl_amount = -2.92,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1DFE739CBA5A5634', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2023-12-03 11:00:00', '2023-12-03 16:45:03', 2128.75895302, 2136.93889354,
    2160.69033732, 2075.53997919, 0.1002,
    -0.3843, -3.85, 'TIME_EXIT', 5.75,
    0, '1h', '2026-03-08T18:36:22.518678'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3843,
    pnl_amount = -3.85,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BE883A076B3A764C', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2023-12-09 23:00:00', '2023-12-10 07:32:40', 4019.41229427, 4038.98823651,
    3959.12110986, 4119.89760163, 0.0974,
    0.487, 4.74, 'TRAILING_STOP', 8.54,
    1, '1h', '2026-03-08T18:36:22.518963'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.487,
    pnl_amount = 4.74,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5A575CB5F065A02F', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-12-13 08:00:00', '2023-12-13 18:31:29', 43266.38994404, 43085.01447411,
    43915.3857932, 42184.73019544, 0.1126,
    0.4192, 4.72, 'TRAILING_STOP', 10.52,
    1, '1h', '2026-03-08T18:36:22.518762'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4192,
    pnl_amount = 4.72,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1A7E29DF0FD0BA55', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2023-12-18 20:00:00', '2023-12-18 23:29:39', 3288.7762727, 3302.1283235,
    3338.10791679, 3206.55686588, 0.0917,
    -0.406, -3.72, 'STOP_LOSS', 3.49,
    0, '1h', '2026-03-08T18:36:22.518280'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.406,
    pnl_amount = -3.72,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '67F4361F9466C3A2', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-12-20 07:00:00', '2023-12-20 17:17:52', 626.5397909, 624.75630416,
    617.14169404, 642.20328568, 0.0986,
    -0.2847, -2.81, 'TIME_EXIT', 10.3,
    0, '1h', '2026-03-08T18:36:22.521103'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2847,
    pnl_amount = -2.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4503EA78D9C89D0C', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2023-12-20 08:00:00', '2023-12-20 17:12:47', 1097.38190015, 1102.46434952,
    1080.92117165, 1124.81644766, 0.102,
    0.4631, 4.73, 'TAKE_PROFIT', 9.21,
    1, '1h', '2026-03-08T18:36:22.517482'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4631,
    pnl_amount = 4.73,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0A57036261296EDA', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-12-20 13:00:00', '2023-12-20 15:44:10', 2603.37275352, 2591.97202804,
    2642.42334483, 2538.28843469, 0.1077,
    0.4379, 4.72, 'TAKE_PROFIT', 2.74,
    1, '1h', '2026-03-08T18:36:22.517644'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4379,
    pnl_amount = 4.72,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '01958072C54ECF55', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2023-12-27 16:00:00', '2023-12-27 18:40:38', 6553.73059373, 6573.83251174,
    6652.03655264, 6389.88732889, 0.0895,
    -0.3067, -2.74, 'STOP_LOSS', 2.68,
    0, '1h', '2026-03-08T18:36:22.518742'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3067,
    pnl_amount = -2.74,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E613542B8435193F', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2023-12-28 01:00:00', '2023-12-28 11:26:19', 699.02743626, 695.72238642,
    709.5128478, 681.55175035, 0.1022,
    0.4728, 4.83, 'TIME_EXIT', 10.44,
    1, '1h', '2026-03-08T18:36:22.522955'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4728,
    pnl_amount = 4.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F676853D7EC71C43', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2024-01-03 18:00:00', '2024-01-03 21:04:06', 1694.80753914, 1689.26139217,
    1669.38542605, 1737.17772762, 0.1051,
    -0.3272, -3.44, 'TIME_EXIT', 3.07,
    0, '1h', '2026-03-08T18:36:22.520830'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3272,
    pnl_amount = -3.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '57A0258F5447BC6F', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-01-04 04:00:00', '2024-01-04 14:32:43', 2136.13233284, 2127.59542308,
    2104.09034785, 2189.53564116, 0.0971,
    -0.3996, -3.88, 'STOP_LOSS', 10.55,
    0, '1h', '2026-03-08T18:36:22.521021'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3996,
    pnl_amount = -3.88,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BBED29A023383FCA', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2024-01-04 21:00:00', '2024-01-05 03:30:39', 4378.72484308, 4365.09632095,
    4313.04397043, 4488.19296416, 0.0932,
    -0.3112, -2.9, 'TIME_EXIT', 6.51,
    0, '1h', '2026-03-08T18:36:22.519922'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3112,
    pnl_amount = -2.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD72A7A99174BC99', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-01-05 12:00:00', '2024-01-05 18:14:22', 4492.99982556, 4519.81465136,
    4425.60482818, 4605.3248212, 0.084,
    0.5968, 5.01, 'TIME_EXIT', 6.24,
    1, '1h', '2026-03-08T18:36:22.519151'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5968,
    pnl_amount = 5.01,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '856D14B0964381E7', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-01-07 01:00:00', '2024-01-07 11:31:15', 2686.46265305, 2694.18196252,
    2726.75959285, 2619.30108673, 0.113,
    -0.2873, -3.25, 'STOP_LOSS', 10.52,
    0, '1h', '2026-03-08T18:36:22.517691'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2873,
    pnl_amount = -3.25,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9C9CA75B1F9C524F', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-01-16 23:00:00', '2024-01-17 02:23:44', 1451.30096188, 1442.76896713,
    1473.07047631, 1415.01843783, 0.113,
    0.5879, 6.64, 'TRAILING_STOP', 3.4,
    1, '1h', '2026-03-08T18:36:22.517764'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5879,
    pnl_amount = 6.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FB6F4ECE88075F75', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-01-18 05:00:00', '2024-01-18 08:26:00', 3489.07772816, 3474.30421202,
    3541.41389408, 3401.85078495, 0.0855,
    0.4234, 3.62, 'TAKE_PROFIT', 3.43,
    1, '1h', '2026-03-08T18:36:22.523195'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4234,
    pnl_amount = 3.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '151386E22E09A170', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-01-20 01:00:00', '2024-01-20 12:07:17', 4867.06017622, 4833.44231747,
    4940.06607886, 4745.38367182, 0.0923,
    0.6907, 6.38, 'TIME_EXIT', 11.12,
    1, '1h', '2026-03-08T18:36:22.522425'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6907,
    pnl_amount = 6.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A241E29B154D405', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-01-22 03:00:00', '2024-01-22 06:16:12', 2055.1908281, 2064.70536637,
    2024.36296567, 2106.5705988, 0.0916,
    0.463, 4.24, 'TAKE_PROFIT', 3.27,
    1, '1h', '2026-03-08T18:36:22.523293'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.463,
    pnl_amount = 4.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F84CD69459E51B6', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-01-23 02:00:00', '2024-01-23 08:46:38', 4459.02413059, 4440.40941919,
    4392.13876863, 4570.49973385, 0.0939,
    -0.4175, -3.92, 'STOP_LOSS', 6.78,
    0, '1h', '2026-03-08T18:36:22.522900'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4175,
    pnl_amount = -3.92,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6173B260D7219342', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2024-01-23 11:00:00', '2024-01-23 13:23:00', 2389.82128007, 2379.10282269,
    2425.66859927, 2330.07574806, 0.1157,
    0.4485, 5.19, 'TRAILING_STOP', 2.38,
    1, '1h', '2026-03-08T18:36:22.518501'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4485,
    pnl_amount = 5.19,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5F61DE49C463E053', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-01-27 07:00:00', '2024-01-27 16:22:31', 392.6326302, 389.7945092,
    398.52211966, 382.81681445, 0.1194,
    0.7228, 8.63, 'TAKE_PROFIT', 9.38,
    1, '1h', '2026-03-08T18:36:22.518129'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7228,
    pnl_amount = 8.63,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0E0B89E91EE235B7', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2024-01-31 06:00:00', '2024-01-31 14:16:10', 3730.25254252, 3716.48437379,
    3674.29875438, 3823.50885608, 0.1165,
    -0.3691, -4.3, 'STOP_LOSS', 8.27,
    0, '1h', '2026-03-08T18:36:22.522689'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3691,
    pnl_amount = -4.3,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7537DE52DDD22EA8', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-02-02 02:00:00', '2024-02-02 08:07:59', 4003.67582875, 4020.15459924,
    3943.62069132, 4103.76772447, 0.1031,
    0.4116, 4.24, 'TAKE_PROFIT', 6.13,
    1, '1h', '2026-03-08T18:36:22.518093'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4116,
    pnl_amount = 4.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A416480F995E765E', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2024-02-04 03:00:00', '2024-02-04 14:23:41', 4445.84135389, 4426.85474492,
    4512.5289742, 4334.69532004, 0.0982,
    0.4271, 4.19, 'TRAILING_STOP', 11.39,
    1, '1h', '2026-03-08T18:36:22.520167'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4271,
    pnl_amount = 4.19,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C79BC90FB0BD9F5F', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2024-02-05 10:00:00', '2024-02-05 20:35:24', 4468.27237012, 4483.80679494,
    4535.29645568, 4356.56556087, 0.1035,
    -0.3477, -3.6, 'STOP_LOSS', 10.59,
    0, '1h', '2026-03-08T18:36:22.523370'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3477,
    pnl_amount = -3.6,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '32BD115BBC627BDA', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2024-02-05 20:00:00', '2024-02-05 22:28:13', 4738.75951904, 4716.84577953,
    4809.84091183, 4620.29053106, 0.1128,
    0.4624, 5.21, 'TAKE_PROFIT', 2.47,
    1, '1h', '2026-03-08T18:36:22.516938'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4624,
    pnl_amount = 5.21,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D607CE5ECECC3172', 'BB_SQUEEZE_v1', 'BNBUSDT', 'LONG',
    '2024-02-05 22:00:00', '2024-02-06 01:14:46', 1022.30471237, 1030.1062007,
    1006.97014168, 1047.86233017, 0.1082,
    0.7631, 8.26, 'TIME_EXIT', 3.25,
    1, '1h', '2026-03-08T18:36:22.519402'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7631,
    pnl_amount = 8.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7E5853C51FFEB19F', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2024-02-06 05:00:00', '2024-02-06 12:29:30', 3448.70593347, 3461.40583976,
    3500.43652248, 3362.48828514, 0.0978,
    -0.3683, -3.6, 'TIME_EXIT', 7.49,
    0, '1h', '2026-03-08T18:36:22.520268'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3683,
    pnl_amount = -3.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '12867AAD68F68136', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2024-02-06 05:00:00', '2024-02-06 07:35:37', 558.188339, 562.27035351,
    549.81551391, 572.14304747, 0.1066,
    0.7313, 7.8, 'TAKE_PROFIT', 2.59,
    1, '1h', '2026-03-08T18:36:22.522177'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7313,
    pnl_amount = 7.8,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A66B6056DF0AD808', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-02-10 10:00:00', '2024-02-10 18:10:26', 3363.27393979, 3385.21700006,
    3312.82483069, 3447.35578829, 0.0904,
    0.6524, 5.9, 'TIME_EXIT', 8.17,
    1, '1h', '2026-03-08T18:36:22.517199'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6524,
    pnl_amount = 5.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '138D2A8DA5AB41E1', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-02-13 08:00:00', '2024-02-13 19:47:08', 3415.23643527, 3402.61785696,
    3364.00788874, 3500.61734615, 0.1168,
    -0.3695, -4.31, 'TIME_EXIT', 11.79,
    0, '1h', '2026-03-08T18:36:22.517064'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3695,
    pnl_amount = -4.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D847EE2DAFD4F622', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-02-13 20:00:00', '2024-02-14 02:04:35', 969.98851884, 966.38603207,
    955.43869106, 994.23823181, 0.1144,
    -0.3714, -4.25, 'STOP_LOSS', 6.08,
    0, '1h', '2026-03-08T18:36:22.523275'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3714,
    pnl_amount = -4.25,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DCB6D07359189EEC', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2024-02-14 17:00:00', '2024-02-15 01:34:47', 2082.94275824, 2076.48051368,
    2051.69861687, 2135.0163272, 0.1017,
    -0.3102, -3.16, 'TIME_EXIT', 8.58,
    0, '1h', '2026-03-08T18:36:22.517006'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3102,
    pnl_amount = -3.16,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B40190D62B285D09', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2024-02-20 08:00:00', '2024-02-20 12:54:39', 26981.02430515, 26843.66520144,
    27385.73966973, 26306.49869752, 0.1188,
    0.5091, 6.05, 'TIME_EXIT', 4.91,
    1, '1h', '2026-03-08T18:36:22.519266'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5091,
    pnl_amount = 6.05,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F5D474CC0B6B9EB', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-02-21 20:00:00', '2024-02-22 02:43:01', 4396.09681501, 4381.55301681,
    4330.15536279, 4505.99923539, 0.1128,
    -0.3308, -3.73, 'STOP_LOSS', 6.72,
    0, '1h', '2026-03-08T18:36:22.520955'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3308,
    pnl_amount = -3.73,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '89201C3BC98EE8C4', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-02-25 22:00:00', '2024-02-26 09:44:29', 2071.99728032, 2081.90623576,
    2040.91732111, 2123.79721232, 0.1124,
    0.4782, 5.38, 'TAKE_PROFIT', 11.74,
    1, '1h', '2026-03-08T18:36:22.519892'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4782,
    pnl_amount = 5.38,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96550D0F1FF87347', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-02-28 03:00:00', '2024-02-28 07:58:54', 3958.48570753, 3936.74670879,
    4017.86299314, 3859.52356484, 0.0953,
    0.5492, 5.23, 'TRAILING_STOP', 4.98,
    1, '1h', '2026-03-08T18:36:22.517981'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5492,
    pnl_amount = 5.23,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '28B2B3F6DD08872A', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2024-03-01 11:00:00', '2024-03-01 18:51:56', 3135.31947799, 3148.0238329,
    3182.34927016, 3056.93649104, 0.1008,
    -0.4052, -4.08, 'TIME_EXIT', 7.87,
    0, '1h', '2026-03-08T18:36:22.517938'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4052,
    pnl_amount = -4.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '94E814DEC8D16F68', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-03-02 19:00:00', '2024-03-03 06:41:23', 41448.76973797, 41660.20964575,
    40827.0381919, 42484.98898142, 0.105,
    0.5101, 5.36, 'TRAILING_STOP', 11.69,
    1, '1h', '2026-03-08T18:36:22.520964'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5101,
    pnl_amount = 5.36,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7DCC9AE4779905D9', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2024-03-05 22:00:00', '2024-03-06 08:54:52', 1222.79676585, 1213.78759506,
    1241.13871734, 1192.2268467, 0.0969,
    0.7368, 7.14, 'TRAILING_STOP', 10.91,
    1, '1h', '2026-03-08T18:36:22.517179'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7368,
    pnl_amount = 7.14,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '990549BBCDD8196C', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2024-03-20 15:00:00', '2024-03-20 20:01:00', 136.7047038, 137.12092905,
    138.75527435, 133.2870862, 0.0959,
    -0.3045, -2.92, 'TIME_EXIT', 5.02,
    0, '1h', '2026-03-08T18:36:22.517797'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3045,
    pnl_amount = -2.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0E922DFCE5DEB765', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2024-03-21 09:00:00', '2024-03-21 11:12:59', 4109.98865154, 4080.41091748,
    4171.63848131, 4007.23893525, 0.1195,
    0.7197, 8.6, 'TAKE_PROFIT', 2.22,
    1, '1h', '2026-03-08T18:36:22.521495'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7197,
    pnl_amount = 8.6,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B48176263AD61B76', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-03-23 22:00:00', '2024-03-24 02:37:54', 4545.57540012, 4529.55316412,
    4477.39176912, 4659.21478512, 0.0955,
    -0.3525, -3.37, 'STOP_LOSS', 4.63,
    0, '1h', '2026-03-08T18:36:22.517221'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3525,
    pnl_amount = -3.37,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '681816847117E0F4', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2024-03-25 12:00:00', '2024-03-25 18:58:06', 38917.63624352, 39065.58239429,
    39501.40078718, 37944.69533744, 0.1064,
    -0.3802, -4.05, 'TIME_EXIT', 6.97,
    0, '1h', '2026-03-08T18:36:22.522643'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3802,
    pnl_amount = -4.05,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F54E08C025C854D', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2024-03-25 14:00:00', '2024-03-25 19:03:33', 202.39926729, 201.45123381,
    205.4352563, 197.33928561, 0.0833,
    0.4684, 3.9, 'TIME_EXIT', 5.06,
    1, '1h', '2026-03-08T18:36:22.518188'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4684,
    pnl_amount = 3.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F9FBE230E88E9953', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2024-03-26 03:00:00', '2024-03-26 10:52:54', 4986.54599753, 4950.57420901,
    5061.34418749, 4861.88234759, 0.0929,
    0.7214, 6.7, 'TAKE_PROFIT', 7.88,
    1, '1h', '2026-03-08T18:36:22.519882'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7214,
    pnl_amount = 6.7,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '35FAE804E9A3B4F6', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2024-03-29 09:00:00', '2024-03-29 13:09:54', 4934.04126251, 4902.57054429,
    5008.05188145, 4810.69023095, 0.1166,
    0.6378, 7.44, 'TRAILING_STOP', 4.17,
    1, '1h', '2026-03-08T18:36:22.521954'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6378,
    pnl_amount = 7.44,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D54681C68C2D0C51', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2024-03-31 21:00:00', '2024-04-01 06:44:47', 2339.99054449, 2323.28625474,
    2375.09040266, 2281.49078088, 0.0846,
    0.7139, 6.04, 'TAKE_PROFIT', 9.75,
    1, '1h', '2026-03-08T18:36:22.519776'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7139,
    pnl_amount = 6.04,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '381FF2CF2315D6AA', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2024-04-05 09:00:00', '2024-04-05 14:52:48', 1338.98996903, 1328.85519541,
    1359.07481857, 1305.51521981, 0.1143,
    0.7569, 8.65, 'TAKE_PROFIT', 5.88,
    1, '1h', '2026-03-08T18:36:22.517961'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7569,
    pnl_amount = 8.65,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D0FDD865E8D3583D', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-04-06 11:00:00', '2024-04-06 17:31:39', 335.43675235, 336.4217701,
    340.46830364, 327.05083354, 0.0934,
    -0.2937, -2.74, 'STOP_LOSS', 6.53,
    0, '1h', '2026-03-08T18:36:22.517150'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2937,
    pnl_amount = -2.74,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '55E35D553339FA52', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-04-08 07:00:00', '2024-04-08 16:40:27', 1599.80734044, 1588.63921851,
    1623.80445055, 1559.81215693, 0.1058,
    0.6981, 7.39, 'TIME_EXIT', 9.67,
    1, '1h', '2026-03-08T18:36:22.521919'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6981,
    pnl_amount = 7.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1D56F0BC047BFB85', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2024-04-23 12:00:00', '2024-04-23 20:41:52', 702.87675924, 700.08606447,
    692.33360785, 720.44867822, 0.1152,
    -0.397, -4.57, 'STOP_LOSS', 8.7,
    0, '1h', '2026-03-08T18:36:22.519661'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.397,
    pnl_amount = -4.57,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ED9A85C04EC62394', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-04-30 17:00:00', '2024-04-30 20:09:04', 3848.94785423, 3833.73181197,
    3791.21363642, 3945.17155059, 0.1065,
    -0.3953, -4.21, 'TIME_EXIT', 3.15,
    0, '1h', '2026-03-08T18:36:22.520990'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3953,
    pnl_amount = -4.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D3C3297A5061C511', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-05-07 23:00:00', '2024-05-08 01:42:07', 2098.88271267, 2092.85007236,
    2067.39947198, 2151.35478048, 0.1105,
    -0.2874, -3.18, 'STOP_LOSS', 2.7,
    0, '1h', '2026-03-08T18:36:22.517632'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2874,
    pnl_amount = -3.18,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EFC392D517A8FA5F', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2024-05-10 17:00:00', '2024-05-10 19:02:15', 2309.90215592, 2301.71575336,
    2275.25362358, 2367.64970982, 0.1116,
    -0.3544, -3.96, 'TIME_EXIT', 2.04,
    0, '1h', '2026-03-08T18:36:22.523352'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3544,
    pnl_amount = -3.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '611D8B25E3827ECA', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-05-11 03:00:00', '2024-05-11 05:29:41', 29080.84592218, 29210.70846228,
    28644.63323335, 29807.86707024, 0.1174,
    0.4466, 5.24, 'TAKE_PROFIT', 2.49,
    1, '1h', '2026-03-08T18:36:22.521605'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4466,
    pnl_amount = 5.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6C7158A8EBC3A9B3', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-05-11 22:00:00', '2024-05-12 04:25:11', 1355.21749735, 1363.14677841,
    1334.88923488, 1389.09793478, 0.0864,
    0.5851, 5.05, 'TAKE_PROFIT', 6.42,
    1, '1h', '2026-03-08T18:36:22.521945'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5851,
    pnl_amount = 5.05,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '00B0AD704FCDCB2F', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2024-05-14 18:00:00', '2024-05-15 03:14:44', 3512.46904622, 3527.20996801,
    3565.15608192, 3424.65732007, 0.0963,
    -0.4197, -4.04, 'STOP_LOSS', 9.25,
    0, '1h', '2026-03-08T18:36:22.517324'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4197,
    pnl_amount = -4.04,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8F9F7ADCBE4E0964', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-05-16 05:00:00', '2024-05-16 07:07:04', 1236.67524653, 1229.36795274,
    1255.22537523, 1205.75836537, 0.1107,
    0.5909, 6.54, 'TAKE_PROFIT', 2.12,
    1, '1h', '2026-03-08T18:36:22.522141'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5909,
    pnl_amount = 6.54,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D7FFC4974CAD012D', 'BB_SQUEEZE_v1', 'DOTUSDT', 'SHORT',
    '2024-05-23 19:00:00', '2024-05-24 00:01:13', 1418.08119665, 1410.80003065,
    1439.3524146, 1382.62916673, 0.0841,
    0.5135, 4.32, 'TAKE_PROFIT', 5.02,
    1, '1h', '2026-03-08T18:36:22.522194'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5135,
    pnl_amount = 4.32,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98BCE8ED8998516C', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-05-28 16:00:00', '2024-05-29 02:35:44', 3882.50866997, 3870.17049874,
    3824.27103992, 3979.57138672, 0.0915,
    -0.3178, -2.91, 'STOP_LOSS', 10.6,
    0, '1h', '2026-03-08T18:36:22.519598'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3178,
    pnl_amount = -2.91,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6AD77EDA5438A9B6', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-06-02 19:00:00', '2024-06-03 06:44:22', 2739.1456005, 2759.45247134,
    2698.05841649, 2807.62424051, 0.1018,
    0.7414, 7.55, 'TAKE_PROFIT', 11.74,
    1, '1h', '2026-03-08T18:36:22.520068'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7414,
    pnl_amount = 7.55,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EBD078B1E37947C4', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-06-08 08:00:00', '2024-06-08 15:47:50', 2624.31880953, 2613.92706817,
    2584.95402739, 2689.92677977, 0.0817,
    -0.396, -3.24, 'TIME_EXIT', 7.8,
    0, '1h', '2026-03-08T18:36:22.519105'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.396,
    pnl_amount = -3.24,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A1166429549CDEE9', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-06-11 11:00:00', '2024-06-11 13:57:25', 47135.30163241, 47384.3788458,
    46428.27210793, 48313.68417322, 0.08,
    0.5284, 4.23, 'TRAILING_STOP', 2.96,
    1, '1h', '2026-03-08T18:36:22.519207'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5284,
    pnl_amount = 4.23,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DCACC44959000918', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-06-15 20:00:00', '2024-06-16 03:46:59', 4774.65775421, 4804.57675933,
    4703.0378879, 4894.02419807, 0.0855,
    0.6266, 5.35, 'TRAILING_STOP', 7.78,
    1, '1h', '2026-03-08T18:36:22.522255'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6266,
    pnl_amount = 5.35,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4DB3283BB219DFF1', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-06-18 06:00:00', '2024-06-18 09:59:03', 702.98776183, 698.37114256,
    713.53257825, 685.41306778, 0.1086,
    0.6567, 7.13, 'TAKE_PROFIT', 3.98,
    1, '1h', '2026-03-08T18:36:22.522782'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6567,
    pnl_amount = 7.13,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '45925E3251DD9E1C', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-06-19 08:00:00', '2024-06-19 17:55:38', 1733.5654374, 1722.80650115,
    1759.56891896, 1690.22630147, 0.106,
    0.6206, 6.58, 'TIME_EXIT', 9.93,
    1, '1h', '2026-03-08T18:36:22.522150'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6206,
    pnl_amount = 6.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C508EE3DF47638A5', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-06-20 21:00:00', '2024-06-20 23:36:20', 4409.03189557, 4391.57533946,
    4342.89641713, 4519.25769296, 0.0969,
    -0.3959, -3.84, 'TIME_EXIT', 2.61,
    0, '1h', '2026-03-08T18:36:22.523028'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3959,
    pnl_amount = -3.84,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3C6769281B92A940', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2024-06-21 17:00:00', '2024-06-22 04:19:11', 4875.86101059, 4895.64152841,
    4802.72309543, 4997.75753586, 0.0877,
    0.4057, 3.56, 'TAKE_PROFIT', 11.32,
    1, '1h', '2026-03-08T18:36:22.517281'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4057,
    pnl_amount = 3.56,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '225B784AEF16FEC9', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-06-26 18:00:00', '2024-06-26 20:41:47', 17997.28813857, 18084.52765174,
    17727.32881649, 18447.22034203, 0.0824,
    0.4847, 3.99, 'TAKE_PROFIT', 2.7,
    1, '1h', '2026-03-08T18:36:22.521990'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4847,
    pnl_amount = 3.99,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '441357AB2129B95D', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-06-29 16:00:00', '2024-06-30 01:16:21', 4934.13619238, 4967.04687216,
    4860.12414949, 5057.48959719, 0.0925,
    0.667, 6.17, 'TIME_EXIT', 9.27,
    1, '1h', '2026-03-08T18:36:22.521065'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.667,
    pnl_amount = 6.17,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2EC13F127CE1F177', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-06-30 12:00:00', '2024-06-30 16:47:30', 245.35422199, 243.55687827,
    249.03453532, 239.22036644, 0.1174,
    0.7326, 8.6, 'TAKE_PROFIT', 4.79,
    1, '1h', '2026-03-08T18:36:22.519374'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7326,
    pnl_amount = 8.6,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '43EAACDE48278033', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2024-07-06 00:00:00', '2024-07-06 05:13:55', 222.25251788, 223.12213052,
    225.58630565, 216.69620494, 0.0976,
    -0.3913, -3.82, 'STOP_LOSS', 5.23,
    0, '1h', '2026-03-08T18:36:22.520973'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3913,
    pnl_amount = -3.82,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '97F3DF758C2BECB4', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-07-14 13:00:00', '2024-07-14 18:16:14', 1724.88853026, 1717.780082,
    1699.0152023, 1768.01074352, 0.0939,
    -0.4121, -3.87, 'STOP_LOSS', 5.27,
    0, '1h', '2026-03-08T18:36:22.522237'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4121,
    pnl_amount = -3.87,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A52E6CC9F7725F9D', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-07-18 04:00:00', '2024-07-18 11:41:11', 5415.22903312, 5449.95804848,
    5334.00059762, 5550.60975895, 0.1037,
    0.6413, 6.65, 'TRAILING_STOP', 7.69,
    1, '1h', '2026-03-08T18:36:22.518337'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6413,
    pnl_amount = 6.65,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '206BFD12B6D5AD6F', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-07-18 14:00:00', '2024-07-19 01:34:44', 1803.08556662, 1810.39792877,
    1776.03928312, 1848.16270579, 0.1165,
    0.4055, 4.72, 'TIME_EXIT', 11.58,
    1, '1h', '2026-03-08T18:36:22.518226'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4055,
    pnl_amount = 4.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '64880F5EE0D0F0AD', 'BB_SQUEEZE_v1', 'BNBUSDT', 'SHORT',
    '2024-07-23 13:00:00', '2024-07-24 00:48:32', 3262.61065266, 3245.58119456,
    3311.54981245, 3181.04538634, 0.0832,
    0.522, 4.34, 'TAKE_PROFIT', 11.81,
    1, '1h', '2026-03-08T18:36:22.522293'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.522,
    pnl_amount = 4.34,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F1F72AE701885E8E', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2024-07-24 02:00:00', '2024-07-24 09:17:55', 141.14798587, 142.11761452,
    139.03076609, 144.67668552, 0.1153,
    0.687, 7.92, 'TIME_EXIT', 7.3,
    1, '1h', '2026-03-08T18:36:22.519913'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.687,
    pnl_amount = 7.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30E96518A02B13B6', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-07-24 11:00:00', '2024-07-24 15:35:12', 503.87703907, 501.11498163,
    511.43519466, 491.2801131, 0.1039,
    0.5482, 5.7, 'TRAILING_STOP', 4.59,
    1, '1h', '2026-03-08T18:36:22.520678'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5482,
    pnl_amount = 5.7,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2C0FE8AE1D5501D8', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-07-27 08:00:00', '2024-07-27 17:21:12', 28172.50635059, 28067.87911139,
    27749.91875533, 28876.81900935, 0.1095,
    -0.3714, -4.07, 'STOP_LOSS', 9.35,
    0, '1h', '2026-03-08T18:36:22.518456'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3714,
    pnl_amount = -4.07,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '59D9BBD5092051B1', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-07-28 08:00:00', '2024-07-28 19:24:29', 1282.24753712, 1287.39948436,
    1301.48125018, 1250.19134869, 0.0865,
    -0.4018, -3.47, 'STOP_LOSS', 11.41,
    0, '1h', '2026-03-08T18:36:22.520345'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4018,
    pnl_amount = -3.47,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D4F03497046A6605', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2024-08-02 17:00:00', '2024-08-03 02:03:12', 2928.17846402, 2906.51748681,
    2972.10114098, 2854.97400242, 0.1001,
    0.7397, 7.41, 'TAKE_PROFIT', 9.05,
    1, '1h', '2026-03-08T18:36:22.522735'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7397,
    pnl_amount = 7.41,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4E55EFAA66419FF2', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-08-07 12:00:00', '2024-08-07 16:53:01', 2557.93836527, 2566.69716746,
    2596.30744075, 2493.98990614, 0.0879,
    -0.3424, -3.01, 'TIME_EXIT', 4.88,
    0, '1h', '2026-03-08T18:36:22.520204'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3424,
    pnl_amount = -3.01,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '469A47DB66091022', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-08-08 12:00:00', '2024-08-08 15:06:11', 21574.84817742, 21506.92379771,
    21251.22545476, 22114.21938186, 0.0952,
    -0.3148, -3.0, 'STOP_LOSS', 3.1,
    0, '1h', '2026-03-08T18:36:22.518543'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3148,
    pnl_amount = -3.0,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A4B335E3B8E17028', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-08-16 02:00:00', '2024-08-16 04:08:13', 72.92209684, 73.3263345,
    71.82826538, 74.74514926, 0.0803,
    0.5543, 4.45, 'TRAILING_STOP', 2.14,
    1, '1h', '2026-03-08T18:36:22.521391'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5543,
    pnl_amount = 4.45,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B2C6D329E1D59F90', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-08-16 05:00:00', '2024-08-16 11:23:26', 3078.37290834, 3068.76872027,
    3032.19731471, 3155.33223104, 0.0813,
    -0.312, -2.54, 'STOP_LOSS', 6.39,
    0, '1h', '2026-03-08T18:36:22.518047'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.312,
    pnl_amount = -2.54,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '831B6813ABF2C24A', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2024-08-19 10:00:00', '2024-08-19 15:26:17', 2747.67397089, 2763.31507494,
    2706.45886133, 2816.36582016, 0.1124,
    0.5692, 6.4, 'TAKE_PROFIT', 5.44,
    1, '1h', '2026-03-08T18:36:22.521236'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5692,
    pnl_amount = 6.4,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '236FAC354DDAEA6C', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-08-20 18:00:00', '2024-08-21 05:23:37', 188.26121381, 189.07951729,
    185.4372956, 192.96774415, 0.1019,
    0.4347, 4.43, 'TRAILING_STOP', 11.39,
    1, '1h', '2026-03-08T18:36:22.522567'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4347,
    pnl_amount = 4.43,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FF0195542308CF72', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2024-08-30 03:00:00', '2024-08-30 13:37:42', 514.17845158, 516.27346817,
    506.46577481, 527.03291287, 0.1045,
    0.4074, 4.26, 'TAKE_PROFIT', 10.63,
    1, '1h', '2026-03-08T18:36:22.522863'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4074,
    pnl_amount = 4.26,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30B47406693E8C5E', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2024-08-30 10:00:00', '2024-08-30 13:24:04', 1160.27580044, 1155.6017241,
    1142.87166343, 1189.28269545, 0.0822,
    -0.4028, -3.31, 'STOP_LOSS', 3.4,
    0, '1h', '2026-03-08T18:36:22.520911'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4028,
    pnl_amount = -3.31,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3B7996B1BAA26722', 'BB_SQUEEZE_v1', 'BNBUSDT', 'SHORT',
    '2024-09-01 14:00:00', '2024-09-01 21:10:49', 670.7604999, 666.14193186,
    680.82190739, 653.9914874, 0.0946,
    0.6886, 6.52, 'TIME_EXIT', 7.18,
    1, '1h', '2026-03-08T18:36:22.518492'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6886,
    pnl_amount = 6.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '491DB6E9645A826E', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-09-05 00:00:00', '2024-09-05 07:37:53', 39019.83345365, 39315.18850514,
    38434.53595184, 39995.32928999, 0.0848,
    0.7569, 6.42, 'TIME_EXIT', 7.63,
    1, '1h', '2026-03-08T18:36:22.521800'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7569,
    pnl_amount = 6.42,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CB2F9F5EE96C815F', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2024-09-06 13:00:00', '2024-09-06 17:51:20', 3454.47572519, 3438.14929241,
    3506.29286107, 3368.11383206, 0.0921,
    0.4726, 4.35, 'TRAILING_STOP', 4.86,
    1, '1h', '2026-03-08T18:36:22.521669'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4726,
    pnl_amount = 4.35,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '725F5BBADC01276B', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-09-09 05:00:00', '2024-09-09 07:58:57', 35303.00161396, 35524.3080121,
    34773.45658975, 36185.57665431, 0.1083,
    0.6269, 6.79, 'TIME_EXIT', 2.98,
    1, '1h', '2026-03-08T18:36:22.519187'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6269,
    pnl_amount = 6.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E659A173CF57EF75', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-09-09 12:00:00', '2024-09-09 22:16:40', 4076.26751701, 4101.57886427,
    4015.12350425, 4178.17420493, 0.1155,
    0.6209, 7.17, 'TRAILING_STOP', 10.28,
    1, '1h', '2026-03-08T18:36:22.522056'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6209,
    pnl_amount = 7.17,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '18DD7450E0CB6CDF', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-09-10 14:00:00', '2024-09-10 20:24:48', 2272.48936594, 2279.9411423,
    2306.57670643, 2215.67713179, 0.109,
    -0.3279, -3.57, 'STOP_LOSS', 6.41,
    0, '1h', '2026-03-08T18:36:22.517252'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3279,
    pnl_amount = -3.57,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9DF51C0BC6ED3B0A', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2024-09-12 22:00:00', '2024-09-13 09:03:36', 2694.11394101, 2705.33019535,
    2653.7022319, 2761.46678954, 0.0831,
    0.4163, 3.46, 'TAKE_PROFIT', 11.06,
    1, '1h', '2026-03-08T18:36:22.519713'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4163,
    pnl_amount = 3.46,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EBF093511017ADCE', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-09-14 17:00:00', '2024-09-14 22:14:10', 883.49004662, 880.98371929,
    870.23769592, 905.57729779, 0.1141,
    -0.2837, -3.24, 'STOP_LOSS', 5.24,
    0, '1h', '2026-03-08T18:36:22.518649'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2837,
    pnl_amount = -3.24,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '00123D9FB17B0472', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-09-15 01:00:00', '2024-09-15 08:41:46', 1015.00396242, 1018.08228123,
    1030.22902186, 989.62886336, 0.1022,
    -0.3033, -3.1, 'TIME_EXIT', 7.7,
    0, '1h', '2026-03-08T18:36:22.522764'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3033,
    pnl_amount = -3.1,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '62D94BC323D375D0', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-09-15 21:00:00', '2024-09-16 07:07:03', 942.77223242, 937.49927537,
    956.91381591, 919.20292661, 0.1081,
    0.5593, 6.05, 'TRAILING_STOP', 10.12,
    1, '1h', '2026-03-08T18:36:22.519568'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5593,
    pnl_amount = 6.05,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BA5287ED12DC5F47', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2024-09-19 07:00:00', '2024-09-19 14:07:14', 1484.91543752, 1477.68428832,
    1507.18916908, 1447.79255158, 0.1077,
    0.487, 5.24, 'TRAILING_STOP', 7.12,
    1, '1h', '2026-03-08T18:36:22.517518'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.487,
    pnl_amount = 5.24,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '28E4DEF1EA570378', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-09-19 14:00:00', '2024-09-19 20:18:46', 4248.07344256, 4279.43364255,
    4184.35234092, 4354.27527863, 0.0903,
    0.7382, 6.66, 'TRAILING_STOP', 6.31,
    1, '1h', '2026-03-08T18:36:22.523082'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7382,
    pnl_amount = 6.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '04278B8A6B2C09FA', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2024-09-20 15:00:00', '2024-09-20 21:35:34', 4579.86403529, 4612.62980128,
    4511.16607476, 4694.36063617, 0.0875,
    0.7154, 6.26, 'TAKE_PROFIT', 6.59,
    1, '1h', '2026-03-08T18:36:22.521678'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7154,
    pnl_amount = 6.26,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A585CA9C421D6391', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2024-09-26 08:00:00', '2024-09-26 15:28:09', 4418.73121693, 4432.07885799,
    4485.01218518, 4308.26293651, 0.1088,
    -0.3021, -3.29, 'STOP_LOSS', 7.47,
    0, '1h', '2026-03-08T18:36:22.522027'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3021,
    pnl_amount = -3.29,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DB9A726CA5FC6C5B', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2024-09-27 21:00:00', '2024-09-28 02:26:40', 4837.28953439, 4805.50953607,
    4909.84887741, 4716.35729603, 0.0864,
    0.657, 5.68, 'TAKE_PROFIT', 5.44,
    1, '1h', '2026-03-08T18:36:22.518289'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.657,
    pnl_amount = 5.68,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '90606A28931C442F', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2024-10-02 00:00:00', '2024-10-02 03:12:39', 76.15085889, 76.57952856,
    75.00859601, 78.05463036, 0.1081,
    0.5629, 6.08, 'TIME_EXIT', 3.21,
    1, '1h', '2026-03-08T18:36:22.517100'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5629,
    pnl_amount = 6.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '69D8324898C8494D', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-10-02 03:00:00', '2024-10-02 06:04:10', 4480.84379502, 4467.5448671,
    4413.63113809, 4592.86488989, 0.1147,
    -0.2968, -3.4, 'TIME_EXIT', 3.07,
    0, '1h', '2026-03-08T18:36:22.518197'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2968,
    pnl_amount = -3.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2567D553D93DDDE2', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-10-03 00:00:00', '2024-10-03 10:13:07', 296.86987152, 298.39358854,
    292.41682345, 304.29161831, 0.0986,
    0.5133, 5.06, 'TRAILING_STOP', 10.22,
    1, '1h', '2026-03-08T18:36:22.522937'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5133,
    pnl_amount = 5.06,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3AABB452DA1484A0', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2024-10-03 06:00:00', '2024-10-03 12:07:51', 4958.50882201, 4942.77539664,
    4884.13118968, 5082.47154256, 0.109,
    -0.3173, -3.46, 'STOP_LOSS', 6.13,
    0, '1h', '2026-03-08T18:36:22.523213'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3173,
    pnl_amount = -3.46,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A4D737628D26C559', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2024-10-03 11:00:00', '2024-10-03 17:06:28', 178.02123116, 177.40053056,
    175.35091269, 182.47176194, 0.0881,
    -0.3487, -3.07, 'STOP_LOSS', 6.11,
    0, '1h', '2026-03-08T18:36:22.518870'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3487,
    pnl_amount = -3.07,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1890CC8A15F43C90', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2024-10-03 12:00:00', '2024-10-03 17:11:47', 2138.65530563, 2152.84517773,
    2106.57547604, 2192.12168827, 0.0842,
    0.6635, 5.58, 'TAKE_PROFIT', 5.2,
    1, '1h', '2026-03-08T18:36:22.523091'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6635,
    pnl_amount = 5.58,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3C0F922EB596DE7E', 'BB_SQUEEZE_v1', 'LINKUSDT', 'SHORT',
    '2024-10-06 05:00:00', '2024-10-06 16:40:03', 2185.81144283, 2193.42855294,
    2218.59861448, 2131.16615676, 0.1065,
    -0.3485, -3.71, 'STOP_LOSS', 11.67,
    0, '1h', '2026-03-08T18:36:22.518999'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3485,
    pnl_amount = -3.71,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C4AE09CB41B2966D', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-10-12 03:00:00', '2024-10-12 06:53:56', 43450.02917565, 43750.87446717,
    42798.27873802, 44536.27990504, 0.1165,
    0.6924, 8.06, 'TIME_EXIT', 3.9,
    1, '1h', '2026-03-08T18:36:22.521331'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6924,
    pnl_amount = 8.06,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2F4655CA6C94AAD1', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2024-10-12 06:00:00', '2024-10-12 13:00:31', 4296.48081211, 4268.92720617,
    4360.92802429, 4189.0687918, 0.1177,
    0.6413, 7.55, 'TIME_EXIT', 7.01,
    1, '1h', '2026-03-08T18:36:22.521381'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6413,
    pnl_amount = 7.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '86D1DE3F6AAB8918', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2024-10-15 04:00:00', '2024-10-15 09:49:47', 4370.14863686, 4392.76442438,
    4304.59640731, 4479.40235278, 0.1095,
    0.5175, 5.67, 'TIME_EXIT', 5.83,
    1, '1h', '2026-03-08T18:36:22.521468'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5175,
    pnl_amount = 5.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '472576D8E4B977B6', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-10-15 19:00:00', '2024-10-16 05:23:56', 8138.58715264, 8171.28308106,
    8016.50834535, 8342.05183145, 0.1037,
    0.4017, 4.17, 'TRAILING_STOP', 10.4,
    1, '1h', '2026-03-08T18:36:22.522881'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4017,
    pnl_amount = 4.17,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '26DC6BC7547A673D', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2024-10-18 05:00:00', '2024-10-18 13:28:43', 3935.04597293, 3950.54304943,
    3876.02028334, 4033.42212226, 0.0855,
    0.3938, 3.37, 'TIME_EXIT', 8.48,
    1, '1h', '2026-03-08T18:36:22.516985'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3938,
    pnl_amount = 3.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FC2E39C7020732BF', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2024-10-23 03:00:00', '2024-10-23 07:10:32', 5270.526691, 5236.69257999,
    5349.58459137, 5138.76352373, 0.1193,
    0.6419, 7.66, 'TIME_EXIT', 4.18,
    1, '1h', '2026-03-08T18:36:22.519670'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6419,
    pnl_amount = 7.66,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ED5DCE3E1C8ED597', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-10-24 11:00:00', '2024-10-24 17:38:02', 672.69493943, 674.96195913,
    682.78536352, 655.87756594, 0.0883,
    -0.337, -2.98, 'TIME_EXIT', 6.63,
    0, '1h', '2026-03-08T18:36:22.522531'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.337,
    pnl_amount = -2.98,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5281F295EB9CF1FF', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2024-10-25 09:00:00', '2024-10-25 18:06:44', 2019.16521637, 2008.36913274,
    2049.45269462, 1968.68608596, 0.1076,
    0.5347, 5.75, 'TAKE_PROFIT', 9.11,
    1, '1h', '2026-03-08T18:36:22.521764'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5347,
    pnl_amount = 5.75,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C0C8AAEA17516604', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-10-26 01:00:00', '2024-10-26 06:57:56', 479.95824195, 483.39940929,
    472.75886832, 491.957198, 0.1171,
    0.717, 8.4, 'TRAILING_STOP', 5.97,
    1, '1h', '2026-03-08T18:36:22.521112'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.717,
    pnl_amount = 8.4,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A4F4A1F9B03DF66', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-10-26 02:00:00', '2024-10-26 10:28:23', 3043.84248213, 3026.70851644,
    3089.50011936, 2967.74642007, 0.0832,
    0.5629, 4.68, 'TAKE_PROFIT', 8.47,
    1, '1h', '2026-03-08T18:36:22.517131'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5629,
    pnl_amount = 4.68,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D3E735DCBB5F3CA3', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2024-10-27 15:00:00', '2024-10-27 20:13:34', 4842.11636352, 4856.01690481,
    4914.74810897, 4721.06345443, 0.084,
    -0.2871, -2.41, 'TIME_EXIT', 5.23,
    0, '1h', '2026-03-08T18:36:22.523231'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2871,
    pnl_amount = -2.41,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '14EE8696A07A16B8', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2024-11-02 20:00:00', '2024-11-03 05:26:19', 10.94105757, 10.89551662,
    10.7769417, 11.21458401, 0.0941,
    -0.4162, -3.92, 'TIME_EXIT', 9.44,
    0, '1h', '2026-03-08T18:36:22.522047'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4162,
    pnl_amount = -3.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CA837ED90ADA8A72', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-11-06 06:00:00', '2024-11-06 16:55:38', 12719.61081912, 12815.21107477,
    12528.81665684, 13037.6010896, 0.1143,
    0.7516, 8.59, 'TRAILING_STOP', 10.93,
    1, '1h', '2026-03-08T18:36:22.521696'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7516,
    pnl_amount = 8.59,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98C0A3C253D1678F', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-11-14 01:00:00', '2024-11-14 08:34:37', 2963.84032144, 2952.37279058,
    3008.29792626, 2889.7443134, 0.1024,
    0.3869, 3.96, 'TAKE_PROFIT', 7.58,
    1, '1h', '2026-03-08T18:36:22.521264'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3869,
    pnl_amount = 3.96,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BA581B1870F7380B', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2024-11-15 23:00:00', '2024-11-16 03:22:11', 1666.9640206, 1655.18819621,
    1691.96848091, 1625.28992009, 0.1151,
    0.7064, 8.13, 'TRAILING_STOP', 4.37,
    1, '1h', '2026-03-08T18:36:22.518601'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7064,
    pnl_amount = 8.13,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5682F34E84D1ADDD', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-11-19 11:00:00', '2024-11-19 17:26:58', 33443.30294012, 33640.58762093,
    32941.65339602, 34279.38551362, 0.1158,
    0.5899, 6.83, 'TIME_EXIT', 6.45,
    1, '1h', '2026-03-08T18:36:22.522540'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5899,
    pnl_amount = 6.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '68F68FB2A6C52449', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2024-11-23 05:00:00', '2024-11-23 15:07:57', 966.02508895, 962.31260676,
    951.53471262, 990.17571618, 0.1049,
    -0.3843, -4.03, 'STOP_LOSS', 10.13,
    0, '1h', '2026-03-08T18:36:22.523311'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3843,
    pnl_amount = -4.03,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E96AA0A525692A89', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2024-11-24 15:00:00', '2024-11-24 18:41:21', 4277.14503394, 4257.71702418,
    4341.30220945, 4170.21640809, 0.1108,
    0.4542, 5.03, 'TIME_EXIT', 3.69,
    1, '1h', '2026-03-08T18:36:22.518420'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4542,
    pnl_amount = 5.03,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A3239232CC49E094', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2024-11-28 19:00:00', '2024-11-29 01:47:33', 1452.59313653, 1459.85783648,
    1430.80423949, 1488.90796495, 0.1049,
    0.5001, 5.25, 'TAKE_PROFIT', 6.79,
    1, '1h', '2026-03-08T18:36:22.519607'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5001,
    pnl_amount = 5.25,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2A8F503BF86FEB4E', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2024-12-01 01:00:00', '2024-12-01 10:01:32', 1195.64223715, 1188.65728256,
    1213.5768707, 1165.75118122, 0.1126,
    0.5842, 6.58, 'TRAILING_STOP', 9.03,
    1, '1h', '2026-03-08T18:36:22.519088'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5842,
    pnl_amount = 6.58,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D68B4CA4D7C8DB2E', 'BB_SQUEEZE_v1', 'ADAUSDT', 'SHORT',
    '2024-12-02 21:00:00', '2024-12-03 01:00:03', 3493.41902478, 3475.95182811,
    3545.82031015, 3406.08354916, 0.0976,
    0.5, 4.88, 'TRAILING_STOP', 4.0,
    1, '1h', '2026-03-08T18:36:22.522001'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5,
    pnl_amount = 4.88,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5A109F1B3239AE23', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2024-12-04 06:00:00', '2024-12-04 12:45:49', 3735.09506097, 3709.45911672,
    3791.12148688, 3641.71768444, 0.0922,
    0.6864, 6.33, 'TRAILING_STOP', 6.76,
    1, '1h', '2026-03-08T18:36:22.522774'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6864,
    pnl_amount = 6.33,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F9BEEEEA6F9620A', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-12-08 21:00:00', '2024-12-09 00:09:55', 2103.19938337, 2110.03357326,
    2134.74737413, 2050.61939879, 0.1174,
    -0.3249, -3.82, 'STOP_LOSS', 3.17,
    0, '1h', '2026-03-08T18:36:22.519959'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3249,
    pnl_amount = -3.82,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D1B34BE06D868EBB', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2024-12-12 10:00:00', '2024-12-12 15:44:55', 36258.69407769, 36399.14416252,
    36802.57448885, 35352.22672574, 0.1075,
    -0.3874, -4.16, 'STOP_LOSS', 5.75,
    0, '1h', '2026-03-08T18:36:22.519722'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3874,
    pnl_amount = -4.16,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '334CDDC12F5577B2', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2024-12-14 04:00:00', '2024-12-14 08:34:13', 613.62962121, 616.20605517,
    622.83406553, 598.28888068, 0.1044,
    -0.4199, -4.38, 'TIME_EXIT', 4.57,
    0, '1h', '2026-03-08T18:36:22.518815'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4199,
    pnl_amount = -4.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DA8BD37F793CA3EA', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-12-20 07:00:00', '2024-12-20 16:22:45', 4568.23919209, 4535.99482551,
    4636.76277998, 4454.03321229, 0.1046,
    0.7058, 7.38, 'TRAILING_STOP', 9.38,
    1, '1h', '2026-03-08T18:36:22.518393'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7058,
    pnl_amount = 7.38,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '725280778CEA1FB7', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-12-20 15:00:00', '2024-12-20 20:39:22', 4427.65812494, 4399.08571825,
    4494.07299681, 4316.96667181, 0.0921,
    0.6453, 5.94, 'TRAILING_STOP', 5.66,
    1, '1h', '2026-03-08T18:36:22.517755'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6453,
    pnl_amount = 5.94,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F7AD1E55946C7BA5', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2024-12-20 18:00:00', '2024-12-20 22:50:45', 3733.51369247, 3747.86084516,
    3789.51639785, 3640.17585015, 0.1027,
    -0.3843, -3.95, 'TIME_EXIT', 4.85,
    0, '1h', '2026-03-08T18:36:22.523109'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3843,
    pnl_amount = -3.95,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FB09CF6065884195', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'SHORT',
    '2024-12-28 02:00:00', '2024-12-28 10:04:53', 3448.07602737, 3429.33418933,
    3499.79716778, 3361.87412668, 0.1072,
    0.5435, 5.83, 'TAKE_PROFIT', 8.08,
    1, '1h', '2026-03-08T18:36:22.523145'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5435,
    pnl_amount = 5.83,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A5DFA1AB4EB82187', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2024-12-30 19:00:00', '2024-12-30 21:35:22', 1275.51316684, 1281.12121984,
    1256.38046934, 1307.40099602, 0.0981,
    0.4397, 4.31, 'TRAILING_STOP', 2.59,
    1, '1h', '2026-03-08T18:36:22.519542'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4397,
    pnl_amount = 4.31,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3BA452FE433264C0', 'BB_SQUEEZE_v1', 'DOTUSDT', 'LONG',
    '2024-12-31 04:00:00', '2024-12-31 07:36:08', 1038.71333411, 1034.55477973,
    1023.1326341, 1064.68116747, 0.1014,
    -0.4004, -4.06, 'TIME_EXIT', 3.6,
    0, '1h', '2026-03-08T18:36:22.522159'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4004,
    pnl_amount = -4.06,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BB401B3D2D4E9CF9', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2025-01-01 03:00:00', '2025-01-01 13:31:25', 4172.95741323, 4158.27392298,
    4110.36305203, 4277.28134856, 0.108,
    -0.3519, -3.8, 'STOP_LOSS', 10.52,
    0, '1h', '2026-03-08T18:36:22.518157'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3519,
    pnl_amount = -3.8,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E2FF9C91787012C8', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2025-01-10 21:00:00', '2025-01-11 05:36:22', 25369.19244425, 25454.47872271,
    25749.73033091, 24734.96263314, 0.1149,
    -0.3362, -3.86, 'TIME_EXIT', 8.61,
    0, '1h', '2026-03-08T18:36:22.521409'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3362,
    pnl_amount = -3.86,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FA514D3F17376C9B', 'BB_SQUEEZE_v1', 'XRPUSDT', 'SHORT',
    '2025-01-16 04:00:00', '2025-01-16 15:52:50', 127.90049409, 126.91893765,
    129.8190015, 124.70298174, 0.1118,
    0.7674, 8.58, 'TIME_EXIT', 11.88,
    1, '1h', '2026-03-08T18:36:22.517590'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7674,
    pnl_amount = 8.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4CA6AECDD153DBA5', 'BB_SQUEEZE_v1', 'SOLUSDT', 'SHORT',
    '2025-01-17 11:00:00', '2025-01-17 21:01:17', 768.51506152, 763.65302083,
    780.04278745, 749.30218499, 0.0812,
    0.6327, 5.14, 'TRAILING_STOP', 10.02,
    1, '1h', '2026-03-08T18:36:22.518356'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6327,
    pnl_amount = 5.14,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '00FEFCF8089518AD', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2025-01-20 03:00:00', '2025-01-20 05:33:17', 2596.65531535, 2616.13383216,
    2557.70548562, 2661.57169823, 0.1077,
    0.7501, 8.08, 'TAKE_PROFIT', 2.55,
    1, '1h', '2026-03-08T18:36:22.523258'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7501,
    pnl_amount = 8.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0A63C0B707431401', 'BB_SQUEEZE_v1', 'LINKUSDT', 'LONG',
    '2025-01-20 12:00:00', '2025-01-20 20:40:43', 4804.00689737, 4840.98034992,
    4731.9467939, 4924.1070698, 0.1006,
    0.7696, 7.74, 'TAKE_PROFIT', 8.68,
    1, '1h', '2026-03-08T18:36:22.518612'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7696,
    pnl_amount = 7.74,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '62B4A58DE5D79EB9', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2025-01-24 10:00:00', '2025-01-24 13:19:08', 3551.12329984, 3531.16440548,
    3604.39014934, 3462.34521734, 0.0898,
    0.562, 5.05, 'TRAILING_STOP', 3.32,
    1, '1h', '2026-03-08T18:36:22.517567'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.562,
    pnl_amount = 5.05,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F3CB08B634E0FEE', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2025-01-24 20:00:00', '2025-01-25 04:06:18', 44547.51876538, 44766.23239624,
    43879.3059839, 45661.20673452, 0.1053,
    0.491, 5.17, 'TAKE_PROFIT', 8.11,
    1, '1h', '2026-03-08T18:36:22.517418'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.491,
    pnl_amount = 5.17,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8DBFD1E644045E6A', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2025-01-25 20:00:00', '2025-01-26 05:19:08', 1249.03199821, 1244.06971742,
    1230.29651824, 1280.25779817, 0.1038,
    -0.3973, -4.13, 'STOP_LOSS', 9.32,
    0, '1h', '2026-03-08T18:36:22.520505'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3973,
    pnl_amount = -4.13,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '319E1536F620D851', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2025-01-27 12:00:00', '2025-01-27 17:36:49', 4904.81861251, 4887.39242904,
    4831.24633333, 5027.43907783, 0.0963,
    -0.3553, -3.42, 'STOP_LOSS', 5.61,
    0, '1h', '2026-03-08T18:36:22.517901'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3553,
    pnl_amount = -3.42,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '532331AD4B9983F1', 'BB_SQUEEZE_v1', 'SOLUSDT', 'LONG',
    '2025-01-31 08:00:00', '2025-01-31 10:43:40', 167.25294582, 168.00147196,
    164.74415164, 171.43426947, 0.1126,
    0.4475, 5.04, 'TAKE_PROFIT', 2.73,
    1, '1h', '2026-03-08T18:36:22.520113'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4475,
    pnl_amount = 5.04,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F8DBA640E3F3D6C', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2025-02-02 06:00:00', '2025-02-02 14:17:53', 11355.7000002, 11276.81944957,
    11526.0355002, 11071.80750019, 0.0815,
    0.6946, 5.66, 'TRAILING_STOP', 8.3,
    1, '1h', '2026-03-08T18:36:22.522488'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6946,
    pnl_amount = 5.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8445AB8F668829E7', 'BB_SQUEEZE_v1', 'ADAUSDT', 'LONG',
    '2025-02-04 00:00:00', '2025-02-04 02:16:23', 4334.73433645, 4351.55578194,
    4269.71332141, 4443.10269487, 0.0851,
    0.3881, 3.3, 'TIME_EXIT', 2.27,
    1, '1h', '2026-03-08T18:36:22.520893'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3881,
    pnl_amount = 3.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '17D3144552884D11', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2025-02-06 18:00:00', '2025-02-07 00:53:01', 471.01739328, 469.68703459,
    463.95213238, 482.79282811, 0.0918,
    -0.2824, -2.59, 'STOP_LOSS', 6.88,
    0, '1h', '2026-03-08T18:36:22.522283'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.2824,
    pnl_amount = -2.59,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '54D26659478B865F', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2025-02-06 22:00:00', '2025-02-07 06:07:16', 3169.40811201, 3156.39357696,
    3216.94923369, 3090.17290921, 0.0993,
    0.4106, 4.08, 'TRAILING_STOP', 8.12,
    1, '1h', '2026-03-08T18:36:22.522744'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4106,
    pnl_amount = 4.08,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '289193DC47FF1B66', 'BB_SQUEEZE_v1', 'MATICUSDT', 'SHORT',
    '2025-02-10 12:00:00', '2025-02-10 16:25:45', 2781.16345828, 2762.22924589,
    2822.88091015, 2711.63437182, 0.0942,
    0.6808, 6.41, 'TRAILING_STOP', 4.43,
    1, '1h', '2026-03-08T18:36:22.519070'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6808,
    pnl_amount = 6.41,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5277E3651A697E48', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2025-02-13 09:00:00', '2025-02-13 13:05:03', 805.25074049, 807.90888819,
    817.3295016, 785.11947198, 0.1024,
    -0.3301, -3.38, 'STOP_LOSS', 4.08,
    0, '1h', '2026-03-08T18:36:22.522074'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3301,
    pnl_amount = -3.38,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B7C87231C7252C53', 'BB_SQUEEZE_v1', 'XRPUSDT', 'LONG',
    '2025-02-13 17:00:00', '2025-02-14 03:07:54', 3559.01512423, 3546.4924747,
    3505.62989736, 3647.99050233, 0.1129,
    -0.3519, -3.97, 'TIME_EXIT', 10.13,
    0, '1h', '2026-03-08T18:36:22.520717'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3519,
    pnl_amount = -3.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5006827F9DF4E419', 'BB_SQUEEZE_v1', 'BTCUSDT', 'SHORT',
    '2025-02-15 19:00:00', '2025-02-16 00:38:39', 17511.93808679, 17583.24099549,
    17774.61715809, 17074.13963462, 0.1101,
    -0.4072, -4.48, 'TIME_EXIT', 5.64,
    0, '1h', '2026-03-08T18:36:22.520176'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4072,
    pnl_amount = -4.48,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '455BA8789F1602B3', 'BB_SQUEEZE_v1', 'ETHUSDT', 'LONG',
    '2025-02-21 16:00:00', '2025-02-21 20:54:59', 1881.29854908, 1888.56388275,
    1853.07907084, 1928.33101281, 0.1125,
    0.3862, 4.35, 'TRAILING_STOP', 4.92,
    1, '1h', '2026-03-08T18:36:22.519506'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.3862,
    pnl_amount = 4.35,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4D13C37698C92C30', 'BB_SQUEEZE_v1', 'ETHUSDT', 'SHORT',
    '2025-02-22 03:00:00', '2025-02-22 05:47:28', 3593.95353325, 3578.22874825,
    3647.86283625, 3504.10469492, 0.1119,
    0.4375, 4.89, 'TRAILING_STOP', 2.79,
    1, '1h', '2026-03-08T18:36:22.520937'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4375,
    pnl_amount = 4.89,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '32D2C20D7473EDDC', 'BB_SQUEEZE_v1', 'BTCUSDT', 'LONG',
    '2025-02-24 11:00:00', '2025-02-24 16:22:38', 24581.75888102, 24682.4700741,
    24213.03249781, 25196.30285305, 0.1123,
    0.4097, 4.6, 'TAKE_PROFIT', 5.38,
    1, '1h', '2026-03-08T18:36:22.519767'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4097,
    pnl_amount = 4.6,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3086D25BB7FD34CD', 'BB_SQUEEZE_v1', 'AVAXUSDT', 'LONG',
    '2025-02-27 12:16:06', '2025-02-27 23:00:00', 3759.55547964, 3745.41828519,
    3703.16214744, 3853.54436663, 0.0816,
    -0.376, -3.07, 'TIME_EXIT', 10.73,
    0, '1h', '2026-03-08T18:36:22.522521'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.376,
    pnl_amount = -3.07,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '56F44872EF10EE43', 'BB_SQUEEZE_v1', 'MATICUSDT', 'LONG',
    '2025-02-27 14:26:15', '2025-02-27 23:00:00', 567.67410116, 565.63861835,
    559.15898964, 581.86595369, 0.0953,
    -0.3586, -3.42, 'STOP_LOSS', 8.56,
    0, '1h', '2026-03-08T18:36:22.522928'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3586,
    pnl_amount = -3.42,
    exit_reason = 'STOP_LOSS';