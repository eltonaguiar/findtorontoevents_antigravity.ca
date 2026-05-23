#!/usr/bin/env python3
'''
NBA Odds Scraper - Fallback for when The Odds API fails
Uses ESPN APIs and balldontlie for game data + odds estimation
to generate value bet predictions.

Usage:
    python nba_odds_scraper.py                    # fetch and display odds
    python nba_odds_scraper.py --save-json        # save to JSON file
    python nba_odds_scraper.py --predict          # generate predictions
'''

import json
import urllib.request
import urllib.error
import datetime
import re
import sys
from typing import Dict, List, Optional, Any

# API Configuration
BALLDONTLIE_API = 'https://api.balldontlie.io/v1'
BALLDONTLIE_KEY = '4db537a0-cca0-458d-b6a7-34f1e4b1a4f3'  # Free tier key

# Canadian sportsbooks for comparison (simulated from public data)
CANADIAN_BOOKS = ['bet365', 'fanduel', 'draftkings', 'betmgm', 'pointsbet', 'caesars']

# Team name mappings
TEAM_MAPPINGS = {
    'LAL': 'Los Angeles Lakers', 'Lakers': 'LAL',
    'BOS': 'Boston Celtics', 'Celtics': 'BOS',
    'GS': 'Golden State Warriors', 'Warriors': 'GS',
    'MIA': 'Miami Heat', 'Heat': 'MIA',
    'DEN': 'Denver Nuggets', 'Nuggets': 'DEN',
    'PHX': 'Phoenix Suns', 'Suns': 'PHX',
    'DAL': 'Dallas Mavericks', 'Mavericks': 'DAL',
    'MIL': 'Milwaukee Bucks', 'Bucks': 'MIL',
    'PHI': 'Philadelphia 76ers', '76ers': 'PHI',
    'NY': 'New York Knicks', 'Knicks': 'NY',
    'CLE': 'Cleveland Cavaliers', 'Cavaliers': 'CLE',
    'SAC': 'Sacramento Kings', 'Kings': 'SAC',
    'OKC': 'Oklahoma City Thunder', 'Thunder': 'OKC',
    'SA': 'San Antonio Spurs', 'Spurs': 'SA',
    'DET': 'Detroit Pistons', 'Pistons': 'DET',
    'TOR': 'Toronto Raptors', 'Raptors': 'TOR',
    'HOU': 'Houston Rockets', 'Rockets': 'HOU',
    'MIN': 'Minnesota Timberwolves', 'Timberwolves': 'MIN',
    'LAC': 'LA Clippers', 'Clippers': 'LAC',
    'BKN': 'Brooklyn Nets', 'Nets': 'BKN',
    'ATL': 'Atlanta Hawks', 'Hawks': 'ATL',
    'ORL': 'Orlando Magic', 'Magic': 'ORL',
    'CHA': 'Charlotte Hornets', 'Hornets': 'CHA',
    'IND': 'Indiana Pacers', 'Pacers': 'IND',
    'CHI': 'Chicago Bulls', 'Bulls': 'CHI',
    'POR': 'Portland Trail Blazers', 'Trail Blazers': 'POR',
    'UTAH': 'Utah Jazz', 'Jazz': 'UTAH',
    'MEM': 'Memphis Grizzlies', 'Grizzlies': 'MEM',
    'NO': 'New Orleans Pelicans', 'Pelicans': 'NO',
    'WSH': 'Washington Wizards', 'Wizards': 'WSH',
}

def fetch_with_key(url: str, api_key: str) -> Optional[Dict]:
    '''Fetch JSON data with API key in header'''
    try:
        req = urllib.request.Request(url)
        req.add_header('Authorization', api_key)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f'Error fetching {url}: {e}', file=sys.stderr)
        return None

def fetch_games_today() -> List[Dict]:
    '''Fetch today's NBA games from balldontlie API'''
    games = []
    today = datetime.date.today()
    
    # Fetch games for today and tomorrow
    for day_offset in range(2):
        check_date = today + datetime.timedelta(days=day_offset)
        date_str = check_date.strftime('%Y-%m-%d')
        
        url = f'{BALLDONTLIE_API}/games?dates[]={date_str}'
        data = fetch_with_key(url, BALLDONTLIE_KEY)
        
        if data and 'data' in data:
            for game in data['data']:
                if game.get('sport', '').lower() == 'nba':
                    games.append({
                        'id': game.get('id'),
                        'date': game.get('date'),
                        'home_team': game.get('home_team', {}).get('full_name'),
                        'home_abbrev': game.get('home_team', {}).get('abbreviation'),
                        'away_team': game.get('visitor_team', {}).get('full_name'),
                        'away_abbrev': game.get('visitor_team', {}).get('abbreviation'),
                        'home_score': game.get('home_team_score'),
                        'away_score': game.get('visitor_team_score'),
                        'status': game.get('status'),
                        'period': game.get('period'),
                        'time': game.get('time'),
                    })
    
    return games

def fetch_nba_standings() -> Dict[str, Dict]:
    '''Fetch current NBA standings from balldontlie'''
    url = f'{BALLDONTLIE_API}/teams'
    data = fetch_with_key(url, BALLDONTLIE_KEY)
    
    teams = {}
    if data and 'data' in data:
        for team in data['data']:
            if team.get('sport', {}).get('abbreviation') == 'nba':
                abbrev = team.get('abbreviation')
                teams[abbrev] = {
                    'name': team.get('full_name'),
                    'abbreviation': abbrev,
                    'conference': team.get('conference'),
                    'division': team.get('division'),
                }
    
    return teams

def fetch_espn_odds() -> Dict[str, Any]:
    '''Fetch odds from ESPN API (free, no key needed)'''
    try:
        url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
        events = []
        competitions = data.get('events', [])
        
        for event in competitions:
            comp = event.get('competitions', [{}])[0]
            venue = comp.get('venue', {})
            
            home_team = comp.get('competitors', [{}])[0].get('team', {})
            away_team = comp.get('competitors', [{}])[1].get('team', {}) if len(comp.get('competitors', [])) > 1 else {}
            
            # Get betting info
            betting = event.get('odds', [{}])[0] if event.get('odds') else {}
            
            game = {
                'id': event.get('id'),
                'date': event.get('date'),
                'status': event.get('status', {}).get('type', {}).get('description'),
                'period': event.get('status', {}).get('period'),
                'clock': event.get('status', {}).get('clock'),
                'home_team': home_team.get('displayName'),
                'home_abbrev': home_team.get('abbreviation'),
                'home_record': home_team.get('record'),
                'away_team': away_team.get('displayName'),
                'away_abbrev': away_team.get('abbreviation'),
                'away_record': away_team.get('record'),
                'venue': venue.get('fullName'),
            }
            
            # Extract betting odds if available
            if betting:
                game['spread'] = betting.get('spread')
                game['over_under'] = betting.get('overUnder')
                game['favorite'] = betting.get('favorite', {}).get('abbreviation')
                
                # Get home/away odds
                for market in betting.get('markets', []):
                    if market.get('key') == 'h2h':
                        for outcome in market.get('outcomes', []):
                            if outcome.get('team') == home_team.get('abbreviation'):
                                game['home_ml'] = outcome.get('odds')
                            elif outcome.get('team') == away_team.get('abbreviation'):
                                game['away_ml'] = outcome.get('odds')
            
            events.append(game)
            
        return {'ok': True, 'games': events, 'count': len(events)}
        
    except Exception as e:
        print(f'ESPN odds fetch error: {e}', file=sys.stderr)
        return {'ok': False, 'games': [], 'error': str(e)}

def estimate_fair_odds(home_win_pct: float, home_ppg: float, away_ppg: float) -> Dict[str, float]:
    '''
    Estimate fair moneyline odds based on team stats
    Uses historical correlation between win% and ML prices
    '''
    # Adjust based on scoring differential
    ppg_diff = (home_ppg - away_ppg) / away_ppg
    win_adj = ppg_diff * 0.5  # 50% weight to scoring
    
    adj_home_win = min(0.95, max(0.05, home_win_pct + win_adj))
    
    # Convert to American odds
    if adj_home_win >= 0.5:
        home_odds = round(-100 * adj_home_win / (1 - adj_home_win))
    else:
        home_odds = round(100 * (1 - adj_home_win) / adj_home_win)
    
    if adj_home_win >= 0.5:
        away_odds = round(-100 * (1 - adj_home_win) / adj_home_win)
    else:
        away_odds = round(100 * adj_home_win / (1 - adj_home_win))
    
    return {
        'home_ml': home_odds,
        'away_ml': away_odds,
        'home_implied_prob': round(1 / (1 + home_odds / 100), 3),
        'away_implied_prob': round(1 / (1 + away_odds / 100), 3),
    }

def calculate_ev(odds: float, win_prob: float) -> float:
    '''Calculate expected value percentage'''
    if odds > 0:
        return (odds / 100 * win_prob) - (1 - win_prob)
    else:
        return ((100 / abs(odds)) * win_prob) - (1 - win_prob)

def generate_value_bets(games: List[Dict], team_stats: Dict) -> List[Dict]:
    '''Generate value bet predictions from games and team stats'''
    predictions = []
    
    for game in games:
        home_abbrev = game.get('home_abbrev')
        away_abbrev = game.get('away_abbrev')
        
        if not home_abbrev or not away_abbrev:
            continue
        
        # Skip if game already completed
        if game.get('status') in ['Final', 'Final/OT']:
            continue
        
        home_stats = team_stats.get(home_abbrev, {})
        away_stats = team_stats.get(away_abbrev, {})
        
        # Get win percentages (estimated from scoring differential)
        home_ppg = home_stats.get('ppg', 9400)
        away_ppg = away_stats.get('ppg', 9400)
        
        # Simple power rating estimate
        home_rating = home_ppg / 9400
        away_rating = away_ppg / 9400
        
        # Home court advantage ~3%
        home_adv = 1.03
        total_rating = home_rating * home_adv + away_rating
        
        home_win_prob = (home_rating * home_adv) / total_rating
        away_win_prob = away_rating / total_rating
        
        # Get actual odds (from ESPN or estimate)
        actual_home_ml = game.get('home_ml')
        actual_away_ml = game.get('away_ml')
        
        if not actual_home_ml or not actual_away_ml:
            # Estimate fair odds
            estimated = estimate_fair_odds(home_win_prob, home_ppg, away_ppg)
            actual_home_ml = estimated['home_ml']
            actual_away_ml = estimated['away_ml']
        
        # Calculate EV for each side
        home_ev = calculate_ev(actual_home_ml, home_win_prob)
        away_ev = calculate_ev(actual_away_ml, away_win_prob)
        
        # Also estimate spread value
        spread = game.get('spread')
        home_spread_ev = 0
        away_spread_ev = 0
        
        pred = {
            'id': f'nba_{game.get("id", "unknown")}_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}',
            'sport': 'NBA',
            'game_id': game.get('id'),
            'date': game.get('date'),
            'status': game.get('status', 'Scheduled'),
            'home_team': game.get('home_team'),
            'home_abbrev': home_abbrev,
            'away_team': game.get('away_team'),
            'away_abbrev': away_abbrev,
            'venue': game.get('venue'),
            'home_record': game.get('home_record'),
            'away_record': game.get('away_record'),
            'home_ppg': home_ppg,
            'away_ppg': away_ppg,
            'home_win_prob': round(home_win_prob * 100, 1),
            'away_win_prob': round(away_win_prob * 100, 1),
            'odds': {
                'home_ml': actual_home_ml,
                'away_ml': actual_away_ml,
                'spread': spread,
                'over_under': game.get('over_under'),
                'favorite': game.get('favorite'),
            },
            'ev': {
                'home_ev': round(home_ev * 100, 1),
                'away_ev': round(away_ev * 100, 1),
            },
            'source': 'nba_odds_scraper_fallback',
            'generated_at': datetime.datetime.now().isoformat(),
        }
        
        # Determine recommendation
        if home_ev > 0.05 and actual_home_ml:
            pred['recommendation'] = {
                'pick': game.get('home_team'),
                'type': 'moneyline',
                'odds': actual_home_ml,
                'ev_pct': round(home_ev * 100, 1),
                'strength': 'STRONG TAKE' if home_ev > 0.15 else 'TAKE' if home_ev > 0.08 else 'LEAN',
            }
        elif away_ev > 0.05 and actual_away_ml:
            pred['recommendation'] = {
                'pick': game.get('away_team'),
                'type': 'moneyline',
                'odds': actual_away_ml,
                'ev_pct': round(away_ev * 100, 1),
                'strength': 'STRONG TAKE' if away_ev > 0.15 else 'TAKE' if away_ev > 0.08 else 'LEAN',
            }
        else:
            pred['recommendation'] = {
                'pick': None,
                'type': 'none',
                'odds': None,
                'ev_pct': 0,
                'strength': 'WAIT',
            }
        
        predictions.append(pred)
    
    return predictions

def get_nba_team_stats() -> Dict[str, Dict]:
    '''Get NBA team stats from ESPN API'''
    try:
        # Fetch standings
        url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode())
        
        teams = {}
        for event in data.get('events', []):
            for competitor in event.get('competitions', [{}])[0].get('competitors', []):
                team = competitor.get('team', {})
                stats = competitor.get('statistics', [])
                
                team_data = {
                    'name': team.get('displayName'),
                    'abbreviation': team.get('abbreviation'),
                    'record': competitor.get('records', [{}])[0].get('summary', ''),
                }
                
                # Parse stats
                for stat in stats:
                    name = stat.get('name', '').lower()
                    value = stat.get('value', '0')
                    try:
                        team_data[name] = float(value)
                    except:
                        team_data[name] = value
                
                abbrev = team.get('abbreviation')
                if abbrev:
                    teams[abbrev] = team_data
        
        return teams
        
    except Exception as e:
        print(f'Error fetching NBA stats: {e}', file=sys.stderr)
        return {}

def main():
    import argparse
    parser = argparse.ArgumentParser(description='NBA Odds Scraper - Fallback for The Odds API')
    parser.add_argument('--save-json', action='store_true', help='Save predictions to JSON file')
    parser.add_argument('--predict', action='store_true', help='Generate value bet predictions')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    print('=' * 60)
    print('NBA Odds Scraper - Fallback Mode')
    print('=' * 60)
    print()
    
    # Fetch ESPN odds (primary free source)
    print('[1/3] Fetching ESPN odds data...')
    espn_data = fetch_espn_odds()
    
    if not espn_data.get('ok'):
        print(f"ESPN fetch failed: {espn_data.get('error')}")
        espn_data = {'ok': False, 'games': []}
    
    print(f'  Found {len(espn_data.get("games", []))} games from ESPN')
    
    # Fetch team stats
    print('[2/3] Fetching NBA team stats...')
    team_stats = get_nba_team_stats()
    print(f'  Got stats for {len(team_stats)} teams')
    
    # Generate predictions
    print('[3/3] Generating value bet predictions...')
    games = espn_data.get('games', [])
    predictions = generate_value_bets(games, team_stats)
    
    result = {
        'ok': True,
        'generated_at': datetime.datetime.now().isoformat(),
        'games_count': len(games),
        'predictions_count': len(predictions),
        'games': games,
        'predictions': predictions,
        'team_stats': team_stats,
        'source': 'nba_odds_scraper_fallback',
    }
    
    # Display results
    print()
    print('=' * 60)
    print('GAMES & PREDICTIONS')
    print('=' * 60)
    
    strong_takes = [p for p in predictions if p.get('recommendation', {}).get('strength') in ['STRONG TAKE', 'TAKE']]
    waits = [p for p in predictions if p.get('recommendation', {}).get('strength') == 'WAIT']
    
    if strong_takes:
        print(f'\nSTRONG TAKES ({len(strong_takes)} bets):')
        for p in strong_takes:
            rec = p.get('recommendation', {})
            ev_pct = rec.get('ev_pct', 0)
            ev_str = '🟢' if ev_pct > 10 else '🟡'
            print(f'  {ev_str} {p["away_team"]} @ {p["home_team"]}')
            print(f'     Pick: {rec.get("pick")} ML {rec.get("odds")} | EV: {ev_pct}%')
            print(f'     Win Prob: Home {p["home_win_prob"]}% | Away {p["away_win_prob"]}%')
            print()
    else:
        print('\nWARNING: No value bets found (all WAIT) - line shopping may not find edge')
    
    print(f'\nSummary:')
    print(f'  Total games: {len(games)}')
    print(f'  Strong takes: {len([p for p in predictions if p.get("recommendation", {}).get("strength") in ["STRONG TAKE", "TAKE"]])}')
    print(f'  Leans: {len([p for p in predictions if p.get("recommendation", {}).get("strength") == "LEAN"])}')
    print(f'  Waits: {len([p for p in predictions if p.get("recommendation", {}).get("strength") == "WAIT"])}')
    
    if args.verbose:
        print('\n📋 Full predictions:')
        for p in predictions:
            print(json.dumps(p, indent=2))
    
    # Save to JSON if requested
    if args.save_json:
        output_file = f'live-monitor/nba_predictions_{datetime.datetime.now().strftime("%Y%m%d")}.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f'\n💾 Saved to {output_file}')
    
    # If --predict, also print for pipeline
    if args.predict:
        print('\nPipeline output:')
        print(json.dumps({
            'predictions': len(predictions),
            'strong_takes': len(strong_takes),
            'source': 'nba_odds_scraper_fallback',
        }))
    
    return result

if __name__ == '__main__':
    main()