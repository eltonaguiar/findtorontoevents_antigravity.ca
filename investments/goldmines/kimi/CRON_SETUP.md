# KIMI Goldmine Cron Setup (Max 10 Jobs)

## Optimized Cron Strategy

Given the **10 cron job limit**, we combine operations efficiently:

## Recommended 10 Cron Jobs

```bash
# === JOB 1: High-frequency data collection (Every 5 minutes) ===
# Combines: stock picks, meme coins, sports value bets
*/5 * * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=collect&source=all&key=goldmine2026" > /dev/null 2>&1

# === JOB 2: Price updates during market hours (Every 15 min, Mon-Fri 9:30-16:00 EST) ===
*/15 9-16 * * 1-5 curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=update_prices&key=goldmine2026" > /dev/null 2>&1

# === JOB 3: Resolve completed picks (Every 30 minutes) ===
*/30 * * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=resolve&key=goldmine2026" > /dev/null 2>&1

# === JOB 4: Daily performance calculation (6:00 AM) ===
0 6 * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=calculate_performance&key=goldmine2026" > /dev/null 2>&1

# === JOB 5: Find winners (6:30 AM - after performance calc) ===
30 6 * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=find_winners&key=goldmine2026" > /dev/null 2>&1

# === JOB 6: Daily snapshot/archive (7:00 AM) ===
0 7 * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=snapshot&key=goldmine2026" > /dev/null 2>&1

# === JOB 7: Weekly deep analysis (Sundays at 8 AM) ===
0 8 * * 0 curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=deep_analysis&key=goldmine2026" > /dev/null 2>&1

# === JOB 8: Cleanup old data (Monthly, 1st at 3 AM) ===
0 3 1 * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=cleanup&key=goldmine2026" > /dev/null 2>&1

# === JOB 9: Backup (Weekly, Sundays at 2 AM) ===
0 2 * * 0 curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=backup&key=goldmine2026" > /dev/null 2>&1

# === JOB 10: Health check + alerts (Every hour) ===
0 * * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=health_check&key=goldmine2026" > /dev/null 2>&1
```

---

## Alternative: SINGLE COMBINED CRON (If you only want 1 job)

Create a `combined_cron.php` that chains all operations:

```php
<?php
// combined_cron.php - Single entry point for all goldmine operations

$key = $_GET['key'] ?? '';
if ($key !== 'goldmine2026') exit;

$hour = date('G');
$minute = date('i');
$dayOfWeek = date('w'); // 0 = Sunday
$dayOfMonth = date('j');

// Always run: collect, update_prices, resolve
file_get_contents('https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=collect&source=all&key=goldmine2026');
file_get_contents('https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=resolve&key=goldmine2026');

// Market hours only: update_prices (9-16, Mon-Fri)
if ($hour >= 9 && $hour <= 16 && $dayOfWeek >= 1 && $dayOfWeek <= 5) {
    file_get_contents('https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=update_prices&key=goldmine2026');
}

// Daily at 6 AM: performance + winners
if ($hour == 6 && $minute < 5) {
    file_get_contents('https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=calculate_performance&key=goldmine2026');
    sleep(5);
    file_get_contents('https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=find_winners&key=goldmine2026');
}

// Daily at 7 AM: snapshot
if ($hour == 7 && $minute < 5) {
    file_get_contents('https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=snapshot&key=goldmine2026');
}

echo "OK";
```

Then just **ONE cron job**:
```bash
*/5 * * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/combined_cron.php?key=goldmine2026" > /dev/null 2>&1
```

---

## Which Strategy to Use?

| Strategy | Cron Jobs Used | Best For |
|----------|---------------|----------|
| **10 separate jobs** | 10 | Maximum flexibility, granular control |
| **1 combined job** | 1 | Maximum efficiency, simple management |
| **Hybrid (recommended)** | 3-4 | Balance of control and efficiency |

---

## Recommended Hybrid (4 Jobs)

```bash
# Job 1: Data collection (every 5 min)
*/5 * * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=collect&source=all&key=goldmine2026" > /dev/null 2>&1

# Job 2: Price updates during market hours
*/15 9-16 * * 1-5 curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=update_prices&key=goldmine2026" > /dev/null 2>&1

# Job 3: Resolve picks (every 30 min)
*/30 * * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=resolve&key=goldmine2026" > /dev/null 2>&1

# Job 4: Daily processing (performance, winners, snapshot, cleanup)
0 6 * * * curl -s "https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_collector.php?action=daily_processing&key=goldmine2026" > /dev/null 2>&1
```

This leaves **6 spare cron jobs** for other system needs!
