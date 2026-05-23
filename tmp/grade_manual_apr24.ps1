# Manual score grading — bypass The Odds API /scores feed (currently returning
# completed_games:0 even though games are final). Posts real ESPN-verified
# final scores to the new grade_manual endpoint on both sports_bets.php
# (lm_sports_bets) and sports_picks.php (lm_sports_daily_picks).
#
# Covers the FULL pending backlog as of 2026-04-25:
#   - 14 active paper tickets in lm_sports_bets (Apr 6 - Apr 25)
#   - 8 yesterday picks + earlier picks in lm_sports_daily_picks
#
# Team names are exact DB values (pulled from sports_bets.php?action=active
# raw response) so the alias matcher in sports_scores_settle_lib.php matches
# on first try. All 14 game records below cover every pending ticket.

$payload = @'
{
  "rows": [
    {"sport":"icehockey_nhl","event_id":"","home_team":"Buffalo Sabres","away_team":"Tampa Bay Lightning","commence_time":"2026-04-06 23:00:00","home_score":4,"away_score":2},
    {"sport":"icehockey_nhl","event_id":"","home_team":"San Jose Sharks","away_team":"Chicago Blackhawks","commence_time":"2026-04-07 02:00:00","home_score":3,"away_score":2},
    {"sport":"icehockey_nhl","event_id":"","home_team":"Montréal Canadiens","away_team":"Florida Panthers","commence_time":"2026-04-07 23:00:00","home_score":4,"away_score":3},
    {"sport":"icehockey_nhl","event_id":"","home_team":"Minnesota Wild","away_team":"Seattle Kraken","commence_time":"2026-04-08 00:00:00","home_score":5,"away_score":2},
    {"sport":"icehockey_nhl","event_id":"","home_team":"Utah Mammoth","away_team":"Edmonton Oilers","commence_time":"2026-04-08 01:30:00","home_score":6,"away_score":5},
    {"sport":"icehockey_nhl","event_id":"","home_team":"Vancouver Canucks","away_team":"Vegas Golden Knights","commence_time":"2026-04-08 02:00:00","home_score":1,"away_score":2},
    {"sport":"soccer_usa_mls","event_id":"","home_team":"Austin FC","away_team":"LA Galaxy","commence_time":"2026-04-11 18:30:00","home_score":1,"away_score":2},
    {"sport":"soccer_usa_mls","event_id":"","home_team":"Charlotte FC","away_team":"Nashville SC","commence_time":"2026-04-11 23:30:00","home_score":1,"away_score":2},
    {"sport":"soccer_usa_mls","event_id":"","home_team":"Colorado Rapids","away_team":"Houston Dynamo","commence_time":"2026-04-12 01:30:00","home_score":6,"away_score":2},
    {"sport":"basketball_nba","event_id":"","home_team":"Minnesota Timberwolves","away_team":"Denver Nuggets","commence_time":"2026-04-24 01:30:00","home_score":113,"away_score":96},
    {"sport":"basketball_nba","event_id":"","home_team":"Atlanta Hawks","away_team":"New York Knicks","commence_time":"2026-04-24 02:00:00","home_score":109,"away_score":108},
    {"sport":"basketball_nba","event_id":"","home_team":"Houston Rockets","away_team":"Los Angeles Lakers","commence_time":"2026-04-25 00:00:00","home_score":108,"away_score":112},
    {"sport":"basketball_nba","event_id":"","home_team":"Portland Trail Blazers","away_team":"San Antonio Spurs","commence_time":"2026-04-25 02:30:00","home_score":108,"away_score":120},
    {"sport":"icehockey_nhl","event_id":"","home_team":"Ottawa Senators","away_team":"Carolina Hurricanes","commence_time":"2026-04-25 19:00:00","home_score":2,"away_score":4}
  ]
}
'@

# UTF-8 byte body so 'Montréal' encodes correctly over the wire.
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)

Write-Host "=== Grading lm_sports_bets (paper tickets) ==="
$r1 = Invoke-WebRequest -UseBasicParsing -Method POST `
    -Uri 'https://findtorontoevents.ca/live-monitor/api/sports_bets.php?action=grade_manual&key=livetrader2026' `
    -ContentType 'application/json; charset=utf-8' -Body $bodyBytes
$r1.Content
Write-Host ""

Write-Host "=== Grading lm_sports_daily_picks (pick history) ==="
$r2 = Invoke-WebRequest -UseBasicParsing -Method POST `
    -Uri 'https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=grade_manual&key=livetrader2026' `
    -ContentType 'application/json; charset=utf-8' -Body $bodyBytes
$r2.Content
Write-Host ""

Write-Host "=== Dashboard after grading ==="
$r3 = Invoke-WebRequest -UseBasicParsing -Uri 'https://findtorontoevents.ca/live-monitor/api/sports_bets.php?action=dashboard'
$r3.Content
