"""
NFL Betting Picks Agent with AI Analysis

This module analyzes NFL player props against projections to identify high-confidence
betting opportunities using both mathematical edge calculations and AI-powered contextual
analysis. It integrates with Grok AI to provide intelligent betting recommendations
based on historical performance, matchups, and market conditions.

Key Features:
- Mathematical edge calculation (projection vs line)
- AI-powered contextual analysis using Grok
- Historical performance analysis
- Weather and matchup context
- Result tracking and feedback
"""

import os
import pandas as pd
import numpy as np
import json
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.search import SearchParameters, web_source, x_source

load_dotenv()

# CONFIGURATION - Easy to adjust
GROK_API_KEY = os.getenv('GROK_API_KEY')
STD_DEV_THRESHOLD = 1.5  # Adjust confidence level
MIN_EDGE_PERCENTAGE = 8.0  # Minimum edge to consider
CONFIDENCE_THRESHOLDS = {
    'high': 80,
    'medium': 60,
    'low': 40
}
GROK_API_URL = "https://api.x.ai/v1/chat/completions"


def load_master_roster():
    """
    Load master roster from Excel file to get player team mappings.
    
    Returns:
        dict: Player name to team abbreviation mapping
    """
    try:
        # Read Excel file
        roster_df = pd.read_excel('data/master_roster.xlsx')
        
        # Create player to team mapping using correct column names
        player_team_mapping = dict(zip(roster_df['Player'], roster_df['team_name']))
        
        print(f"Loaded {len(player_team_mapping)} player-team mappings from master_roster.xlsx")
        return player_team_mapping
    except Exception as e:
        print(f"Error loading master roster: {e}")
        return {}


def load_team_name_mapping():
    """
    Load team name mapping from Excel file.
    
    Returns:
        dict: Full team name to abbreviation mapping
    """
    try:
        # Read Excel file
        team_df = pd.read_excel('data/team_map.xlsx')
        
        # Create team name to abbreviation mapping
        team_mapping = dict(zip(team_df['full_team_name'], team_df['team_abbrev']))
        
        print(f"Loaded {len(team_mapping)} team mappings from team_map.xlsx")
        return team_mapping
    except Exception as e:
        print(f"Error loading team mapping: {e}")
        # Fallback to hardcoded mapping if file fails
        return {
            'Arizona Cardinals': 'ARI',
            'Atlanta Falcons': 'ATL',
            'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF',
            'Carolina Panthers': 'CAR',
            'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN',
            'Cleveland Browns': 'CLE',
            'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN',
            'Detroit Lions': 'DET',
            'Green Bay Packers': 'GNB',
            'Houston Texans': 'HOU',
            'Indianapolis Colts': 'IND',
            'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KAN',
            'Las Vegas Raiders': 'LVR',
            'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LAR',
            'Miami Dolphins': 'MIA',
            'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NWE',
            'New Orleans Saints': 'NOR',
            'New York Giants': 'NYG',
            'New York Jets': 'NYJ',
            'Philadelphia Eagles': 'PHI',
            'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SFO',
            'Seattle Seahawks': 'SEA',
            'Tampa Bay Buccaneers': 'TAM',
            'Tennessee Titans': 'TEN',
            'Washington Commanders': 'WAS'
        }


def determine_opponent(player_name, home_team, away_team, roster_mapping, player_mapping, team_name_mapping):
    """
    Determine the opponent team for a player using roster data and player mapping.
    
    Args:
        player_name (str): Player name from odds data
        home_team (str): Home team full name
        away_team (str): Away team full name
        roster_mapping (dict): Projection name to team mapping
        player_mapping (dict): Odds name to projection name mapping
        team_name_mapping (dict): Full team name to abbreviation mapping
    
    Returns:
        str: Opponent team full name
    """
    # Convert team names to abbreviations
    home_team_abbr = team_name_mapping.get(home_team, home_team)
    away_team_abbr = team_name_mapping.get(away_team, away_team)
    
    # First, try to find the player in roster using the odds name directly
    if player_name in roster_mapping:
        player_team = roster_mapping[player_name]
        # Return the team that's NOT the player's team
        return away_team if player_team == home_team_abbr else home_team
    
    # If not found, try using the player mapping to get projection name
    if player_name in player_mapping:
        projection_name = player_mapping[player_name]
        if projection_name in roster_mapping:
            player_team = roster_mapping[projection_name]
            # Return the team that's NOT the player's team
            return away_team if player_team == home_team_abbr else home_team
    
    # Fallback: assume player is on home team
    print(f"Warning: Player {player_name} not found in roster or mapping, defaulting to away team as opponent")
    return away_team


def create_player_mapping():
    """
    Create mapping between odds player names and projection player names.
    
    Returns:
        dict: Mapping of odds names to projection names
    """
    # Try to load comprehensive mapping first
    mapping_file = 'data/player_name_mapping.csv'
    if os.path.exists(mapping_file):
        try:
            mapping_df = pd.read_csv(mapping_file)
            mapping = dict(zip(mapping_df['odds_name'], mapping_df['projection_name']))
            print(f"Loaded {len(mapping)} player mappings from {mapping_file}")
            return mapping
        except Exception as e:
            print(f"Warning: Could not load mapping file: {e}")
    return {}

def calculate_player_edge(projection, line, prop_type):
    """
    Calculate edge percentage for player props.
    
    Args:
        projection (float): Projected player performance
        line (float): Betting line/over-under
        prop_type (str): Type of prop (rush_yds, rec_yds, etc.)
    
    Returns:
        float: Edge percentage
    """
    # Initialize edge variable to ensure it's always defined
    edge = 0.0
    
    if prop_type in ['rush_yds', 'reception_yds', 'pass_yds', 'receptions', 'pass_attempts', 'pass_completions', 'pass_tds', 'pass_interceptions', 'rush_att']:
        # For all numeric props, use the standard edge calculation
        edge = ((projection - line) / line) * 100
    elif prop_type == 'anytime_td':
        # Convert odds to implied probability
        if line > 0:
            implied_prob = 100 / (line + 100)
        else:
            implied_prob = abs(line) / (abs(line) + 100)
        # Use projection probability (you'll need to add this to projections)
        edge = (projection - implied_prob) * 100
    else:
        # Handle unsupported prop types
        print(f"Warning: Unsupported prop type '{prop_type}' for edge calculation")
        edge = 0.0
    
    return edge


def identify_high_confidence_bets(projections_df, player_props_df, mapping):
    """
    Find bets meeting edge and confidence criteria.
    
    Args:
        projections_df (DataFrame): Player projections data
        player_props_df (DataFrame): Player props odds data
        mapping (dict): Player name mapping
    
    Returns:
        list: List of high confidence betting opportunities
    """
    high_confidence_bets = []
    
    # Debug: Show unique prop types in the data
    unique_prop_types = player_props_df['prop_type'].unique()
    print(f"Found prop types: {unique_prop_types}")
    
    # Track best odds for each unique player/prop combination
    best_odds_tracker = {}
    
    for _, prop in player_props_df.iterrows():
        player_name = prop['player_name']
        if player_name in mapping:
            projection_name = mapping[player_name]
            projection_data = projections_df[projections_df['name'] == projection_name]
            
            if not projection_data.empty:
                prop_type = prop['prop_type']
                line = prop['point']
                odds = prop['price']
                
                # Create unique key for this player/prop combination
                unique_key = (player_name, prop_type, line)
                
                # Get projection based on prop type using actual column names
                if prop_type == 'rush_yds':
                    projection = projection_data['proj_rush_yd'].iloc[0]
                elif prop_type == 'reception_yds':  # Note: odds uses 'reception_yds', projections use 'proj_rec_yd'
                    projection = projection_data['proj_rec_yd'].iloc[0]
                elif prop_type == 'receptions':
                    projection = projection_data['proj_rec'].iloc[0]
                elif prop_type == 'pass_yds':
                    projection = projection_data['proj_pass_yd'].iloc[0]
                elif prop_type == 'pass_attempts':
                    projection = projection_data['proj_pass_att'].iloc[0]
                elif prop_type == 'pass_completions':
                    # Use pass attempts * completion rate (approximate)
                    pass_att = projection_data['proj_pass_att'].iloc[0]
                    # Assume 65% completion rate as default
                    projection = pass_att * 0.65
                elif prop_type == 'pass_tds':
                    projection = projection_data['proj_pass_td'].iloc[0]
                elif prop_type == 'pass_interceptions':
                    projection = projection_data['proj_int'].iloc[0]
                elif prop_type == 'rush_att':
                    projection = projection_data['proj_rush_att'].iloc[0]
                elif prop_type == 'anytime_td':
                    # Use TD projections from actual data
                    rush_td = projection_data['proj_rush_td'].iloc[0]
                    rec_td = projection_data['proj_rec_td'].iloc[0]
                    projection = rush_td + rec_td
                else:
                    print(f"Warning: Unsupported prop type '{prop_type}' - skipping")
                    continue
                
                # Calculate edge
                edge = calculate_player_edge(projection, line, prop_type)
                
                # Calculate standard deviations (using projection variance)
                # For now, use a simple approach - adjust this based on results
                std_dev = line * 0.15  # Assume 15% variance - adjust this
                deviations = abs(projection - line) / std_dev
                
                if edge >= MIN_EDGE_PERCENTAGE and deviations >= STD_DEV_THRESHOLD:
                    confidence = 'high' if deviations >= 2.0 else 'medium' if deviations >= 1.5 else 'low'
                    
                    bet_data = {
                        'player_name': player_name,
                        'prop_type': prop_type,
                        'line': line,
                        'projection': projection,
                        'edge_percentage': edge,
                        'standard_deviations': deviations,
                        'confidence': confidence,
                        'odds': odds,
                        'event_id': prop['event_id'],
                        'home_team': prop['home_team'],
                        'away_team': prop['away_team']
                    }
                    
                    # Check if we already have this player/prop combination
                    if unique_key in best_odds_tracker:
                        # Keep the entry with the maximum odds (best value for bettor)
                        existing_odds = best_odds_tracker[unique_key]['odds']
                        if odds > existing_odds:
                            # Replace with better odds
                            best_odds_tracker[unique_key] = bet_data
                    else:
                        # First time seeing this combination
                        best_odds_tracker[unique_key] = bet_data
    
    # Convert tracker to list
    high_confidence_bets = list(best_odds_tracker.values())
    
    print(f"Eliminated duplicates: {len(high_confidence_bets)} unique bets found")
    
    return high_confidence_bets


def get_historical_performance(player_name, opponent, weeks_back=3):
    """
    Get player's historical performance against specific opponent and recent form.
    
    Args:
        player_name (str): Player name to analyze
        opponent (str): Opponent team abbreviation
        weeks_back (int): Number of recent weeks to analyze
    
    Returns:
        dict: Historical performance data
    """
    try:
        # Load historical game data
        historical_data = []
        for year in [2024, 2023, 2022]:  # Last 3 years
            file_path = f'data/game_data_{year}.csv'
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                player_games = df[df['player'] == player_name]
                historical_data.append(player_games)
        
        if not historical_data:
            return {'error': 'No historical data found'}
        
        all_games = pd.concat(historical_data, ignore_index=True)
        
        # Get games vs this opponent
        vs_opponent = all_games[all_games['opponent'] == opponent]
        
        # Get recent games (last N weeks)
        recent_games = all_games.tail(weeks_back * 2)  # Approximate recent games
        
        performance = {
            'vs_opponent_games': len(vs_opponent),
            'recent_games': len(recent_games),
            'avg_snap_pct': recent_games['snap_pct'].mean() if not recent_games.empty else 0,
            'avg_targets': recent_games['targets'].mean() if not recent_games.empty else 0,
            'avg_receptions': recent_games['receptions'].mean() if not recent_games.empty else 0,
            'avg_rec_yds': recent_games['rec_yds'].mean() if not recent_games.empty else 0,
            'avg_rush_yds': recent_games['rush_yds'].mean() if not recent_games.empty else 0,
            'avg_pass_yds': recent_games['pass_yds'].mean() if not recent_games.empty else 0,
            'weather_conditions': recent_games['weather'].iloc[-1] if not recent_games.empty else 'Unknown'
        }
        
        return performance
    except Exception as e:
        return {'error': f'Error analyzing historical data: {str(e)}'}


def build_player_context(player_name, prop_type, line, projection, opponent, week):
    """
    Build comprehensive context for a single player bet.
    
    Args:
        player_name (str): Player name
        prop_type (str): Type of prop bet
        line (float): Betting line
        projection (float): Model projection
        opponent (str): Opponent team
        week (int): Week number
    
    Returns:
        dict: Complete player context for AI analysis
    """
    # Get historical performance
    historical = get_historical_performance(player_name, opponent)
    
    # Calculate mathematical edge
    edge = calculate_player_edge(projection, line, prop_type)
    
    context = {
        'player': player_name,
        'prop_type': prop_type,
        'line': line,
        'projection': projection,
        'edge_percentage': edge,
        'opponent': opponent,
        'week': week,
        'historical_performance': historical,
        'analysis_timestamp': datetime.now().isoformat()
    }
    
    return context


def get_live_search_context(player_name, week, opponent=None):
    """
    Get live search context for a player using Grok's live search functionality.
    
    Args:
        player_name (str): Player name to search for
        week (int): Current week number
        opponent (str, optional): Opponent team (for context in search prompt)
    
    Returns:
        dict: Live search context including injuries, news, and expert insights
    """
    if not GROK_API_KEY:
        return {'error': 'GROK_API_KEY not found for live search'}
    
    try:
        # Initialize X.AI client
        client = Client(api_key=GROK_API_KEY)
        
        # Create conversation for live search
        chat = client.chat.create(
            model="grok-4",
            search_parameters=SearchParameters(
                max_search_results=5,
                return_citations=True,
                from_date=datetime.now() - timedelta(days=2),
                sources=[
                    web_source(allowed_websites=["https://www.nfl.com/news/", 
                                                 "https://www.nfl.com/injuries/"
                                                 "https://www.espn.com/nfl/"]),
                    x_source(included_x_handles=["rapsheet", "adamschefter"])
                ]
            )
        )
        
        # Create search prompt
        system_prompt = f"""
You are an expert NFL betting analyst with deep knowledge of player performance, matchups, and market conditions. Use live search to get the most current information when needed.
"""

        
        # Build search prompt with optional opponent context
        opponent_context = f"Opponent: {opponent}" if opponent else "Current team and upcoming games"
        
        search_prompt = f"""
Search for current information about {player_name} for Week {week} NFL games. Focus on:

1. Injury status and practice participation from NFL.com/injuries
2. Recent news and developments from ESPN.com/nfl and NFL.com/news
3. Expert analysis from RapSheet and AdamSchefter
4. Weather conditions for the game
5. Role changes or lineup adjustments

Player: {player_name}
{opponent_context}
Week: {week}
"""
        
        # Perform live search with domain restrictions
        chat.append(system(system_prompt))
        chat.append(user(search_prompt))
        response = chat.sample()
        
        return {
            'success': True,
            'live_search_results': response.content,
            'player': player_name,
            'opponent': opponent,
            'week': week
        }
        
    except Exception as e:
        return {'error': f'Live search failed: {str(e)}'}


def call_grok_api(prompt, include_live_search=True):
    """
    Make API call to Grok using X.AI SDK with optional live search.
    
    Args:
        prompt (str): Formatted prompt for Grok
        include_live_search (bool): Whether to enable live search functionality
    
    Returns:
        dict: Grok's response or error
    """
    if not GROK_API_KEY:
        return {'error': 'GROK_API_KEY not found in environment variables'}
    
    try:
        # Initialize X.AI client
        client = Client(api_key=GROK_API_KEY)
        
        # Create a conversation using the correct API
        chat = client.chat.create(model="grok-3")
        
        # Combine system message and user prompt
        if include_live_search:
            full_prompt = f"""You are an expert NFL betting analyst with deep knowledge of player performance, matchups, and market conditions. Use live search to get the most current information when needed.

{prompt}"""
        else:
            full_prompt = f"""You are an expert NFL betting analyst with deep knowledge of player performance, matchups, and market conditions.

{prompt}"""
        
        # Add user prompt and get response
        chat.append(system(full_prompt))
        response = chat.sample()
        
        return {
            'success': True,
            'analysis': response.content
        }
        
    except Exception as e:
        return {'error': f'X.AI API request failed: {str(e)}'}


def generate_ai_analysis_prompt(player_contexts):
    """
    Create focused prompt for Grok AI analysis with live search context.
    
    Args:
        player_contexts (list): List of player context dictionaries with live search data
    
    Returns:
        str: Formatted prompt for Grok
    """
    # Filter to top candidates with good edges - increased to 25
    top_candidates = [ctx for ctx in player_contexts if ctx['edge_percentage'] >= MIN_EDGE_PERCENTAGE]
    top_candidates = sorted(top_candidates, key=lambda x: x['edge_percentage'], reverse=True)[:25]
    
    if not top_candidates:
        return "No qualifying betting opportunities found with sufficient edge."
    
    prompt = f"""
You are an expert NFL betting analyst. Analyze these top 25 betting opportunities for Week {top_candidates[0]['week']} using both historical data and real-time information:

"""
    
    for i, ctx in enumerate(top_candidates, 1):
        # Include live search results if available
        live_search_info = ""
        if 'live_search_results' in ctx and ctx['live_search_results']:
            live_search_info = f"\nLive Search Results: {ctx['live_search_results']}"
        
        prompt += f"""
OPPORTUNITY {i}:
Player: {ctx['player']}
Prop: {ctx['prop_type']} {ctx['line']}
Projection: {ctx['projection']:.1f}
Edge: {ctx['edge_percentage']:.1f}%
Opponent: {ctx['opponent']}
Recent Performance: {ctx['historical_performance'].get('avg_snap_pct', 0):.1f}% snaps, {ctx['historical_performance'].get('avg_targets', 0):.1f} targets
Weather: {ctx['historical_performance'].get('weather_conditions', 'Unknown')}
Latest News and Expert Insights: {live_search_info}

"""
    
    prompt += """
Based on this comprehensive data (historical performance + real-time information), select the TOP 10 betting opportunities and provide:

1. PLAYER NAME
2. PROP TYPE and LINE
3. RECOMMENDATION (Over/Under/Yes/No)
4. CONFIDENCE LEVEL (High/Medium/Low)
5. KEY REASONING (2-3 sentences explaining why this bet is strong)
6. RISK FACTORS (What could go wrong)

Focus on:
- Player's recent form and snap percentage trends
- Historical performance vs this opponent
- Current injury status and practice participation
- Recent news and developments
- Expert analysis and insider information
- Weather conditions and their impact
- Projection vs line edge
- Market context and value

Use live search to get the most current information when needed. Return your analysis in a clear, structured format.
"""
    
    return prompt


def save_ai_insights(week_number, ai_analysis, player_contexts):
    """
    Save AI analysis insights to JSON file.
    
    Args:
        week_number (int): NFL week number
        ai_analysis (dict): Grok's analysis response
        player_contexts (list): Player context data used for analysis
    """
    insights_dir = "data/insights"
    os.makedirs(insights_dir, exist_ok=True)
    
    insights_data = {
        'week': week_number,
        'analysis_timestamp': datetime.now().isoformat(),
        'ai_analysis': ai_analysis,
        'player_contexts': player_contexts,
        'analysis_metadata': {
            'total_opportunities_analyzed': len(player_contexts),
            'edge_threshold': MIN_EDGE_PERCENTAGE,
            'std_dev_threshold': STD_DEV_THRESHOLD
        }
    }
    
    filename = f"{insights_dir}/grok_insights_week_{week_number:02d}.json"
    with open(filename, 'w') as f:
        json.dump(insights_data, f, indent=2)
    
    print(f"Saved AI insights to {filename}")


def analyze_with_ai(week_number):
    """
    Perform AI-powered analysis of betting opportunities.
    
    Args:
        week_number (int): NFL week number to analyze
    
    Returns:
        dict: AI analysis results
    """
    print(f"Starting AI analysis for Week {week_number}...")
    
    # Load data
    if week_number == 0:
        projections_file = 'data/projections/nfl25_proj_week0.csv'
    else:
        projections_file = f'data/projections/nfl25_proj_week{week_number}.csv'
    
    if not os.path.exists(projections_file):
        print(f"Warning: {projections_file} not found, using week 0 projections")
        projections_file = 'data/projections/nfl25_proj_week0.csv'
    
    projections_df = pd.read_csv(projections_file)
    player_props_df = pd.read_csv(f'data/odds/week_{week_number:02d}/player_props_week_{week_number:02d}.csv')
    
    # Create player mapping and load roster data
    mapping = create_player_mapping()
    roster_mapping = load_master_roster()
    team_name_mapping = load_team_name_mapping()
    
    # Build player contexts for AI analysis
    player_contexts = []
    
    for _, prop in player_props_df.iterrows():
        player_name = prop['player_name']
        if player_name in mapping:
            projection_name = mapping[player_name]
            projection_data = projections_df[projections_df['name'] == projection_name]
            
            if not projection_data.empty:
                prop_type = prop['prop_type']
                line = prop['point']
                odds = prop['price']
                
                # Get projection based on prop type
                projection = None
                if prop_type == 'rush_yds':
                    projection = projection_data['proj_rush_yd'].iloc[0]
                elif prop_type == 'reception_yds':
                    projection = projection_data['proj_rec_yd'].iloc[0]
                elif prop_type == 'receptions':
                    projection = projection_data['proj_rec'].iloc[0]
                elif prop_type == 'pass_yds':
                    projection = projection_data['proj_pass_yd'].iloc[0]
                elif prop_type == 'pass_attempts':
                    projection = projection_data['proj_pass_att'].iloc[0]
                elif prop_type == 'pass_completions':
                    pass_att = projection_data['proj_pass_att'].iloc[0]
                    projection = pass_att * 0.65  # Assume 65% completion rate
                elif prop_type == 'pass_tds':
                    projection = projection_data['proj_pass_td'].iloc[0]
                elif prop_type == 'pass_interceptions':
                    projection = projection_data['proj_int'].iloc[0]
                elif prop_type == 'rush_att':
                    projection = projection_data['proj_rush_att'].iloc[0]
                elif prop_type == 'anytime_td':
                    rush_td = projection_data['proj_rush_td'].iloc[0]
                    rec_td = projection_data['proj_rec_td'].iloc[0]
                    projection = rush_td + rec_td
                
                if projection is not None:
                    # Determine opponent using roster data and player mapping
                    opponent = determine_opponent(
                        player_name=player_name,
                        home_team=prop['home_team'],
                        away_team=prop['away_team'],
                        roster_mapping=roster_mapping,
                        player_mapping=mapping,
                        team_name_mapping=team_name_mapping
                    )
                    
                    # Build context for this player
                    context = build_player_context(
                        player_name=player_name,
                        prop_type=prop_type,
                        line=line,
                        projection=projection,
                        opponent=opponent,
                        week=week_number
                    )
                    
                    # Add additional prop data
                    context.update({
                        'odds': odds,
                        'event_id': prop['event_id'],
                        'home_team': prop['home_team'],
                        'away_team': prop['away_team']
                    })
                    
                    player_contexts.append(context)
    
    print(f"Built context for {len(player_contexts)} player props")
    
    # Add live search context for top candidates (with caching to avoid duplicates)
    print("Gathering live search context for top candidates...")
    top_candidates = [ctx for ctx in player_contexts if ctx['edge_percentage'] >= MIN_EDGE_PERCENTAGE]
    top_candidates = sorted(top_candidates, key=lambda x: x['edge_percentage'], reverse=True)[:25]
    
    # Cache for live search results to avoid duplicate requests
    live_search_cache = {}
    unique_players = set()
    
    # First pass: identify unique players
    for context in top_candidates:
        unique_players.add(context['player'])
    
    print(f"Found {len(unique_players)} unique players out of {len(top_candidates)} candidates")
    
    # Second pass: get live search for unique players only
    for i, player in enumerate(unique_players, 1):
        print(f"Getting live search for {player} ({i}/{len(unique_players)})...")
        live_search = get_live_search_context(
            player, 
            week_number  # We don't need opponent for caching
        )
        
        if 'error' not in live_search:
            live_search_cache[player] = live_search.get('live_search_results', '')
        else:
            print(f"Live search failed for {player}: {live_search['error']}")
            live_search_cache[player] = ''
    
    # Third pass: assign cached results to all contexts
    for context in top_candidates:
        context['live_search_results'] = live_search_cache.get(context['player'], '')
    
    # Generate AI prompt with live search context
    prompt = generate_ai_analysis_prompt(player_contexts)
    
    # Call Grok API with live search enabled
    print("Calling Grok AI for analysis with live search...")
    ai_response = call_grok_api(prompt, include_live_search=True)
    
    if 'error' in ai_response:
        print(f"AI analysis failed: {ai_response['error']}")
        return {'error': ai_response['error']}
    
    # Save insights
    save_ai_insights(week_number, ai_response, player_contexts)
    
    print("AI analysis completed successfully!")
    return {
        'success': True,
        'analysis': ai_response['analysis'],
        'player_contexts': player_contexts,
        'usage': ai_response.get('usage', {})
    }


def get_available_weeks():
    """
    Get list of available weeks with odds data.
    
    Returns:
        list: Available week numbers
    """
    odds_dir = "data/odds"
    if not os.path.exists(odds_dir):
        return []
    
    available_weeks = []
    for item in os.listdir(odds_dir):
        if item.startswith("week_") and os.path.isdir(os.path.join(odds_dir, item)):
            try:
                week_num = int(item.split("_")[1])
                available_weeks.append(week_num)
            except ValueError:
                continue
    
    return sorted(available_weeks)


def main(week_number=1, use_ai=True):
    """
    Main execution function for weekly betting analysis.
    
    Args:
        week_number (int): NFL week number to analyze
        use_ai (bool): Whether to use AI analysis (default: True)
    
    Returns:
        dict: Analysis results including AI insights if enabled
    """
    print(f"=== NFL Betting Analysis - Week {week_number} ===")
    print(f"AI Analysis: {'Enabled' if use_ai else 'Disabled'}")
    print()
    
    if use_ai:
        # Use AI-powered analysis
        ai_results = analyze_with_ai(week_number)
        
        if 'error' in ai_results:
            print(f"AI analysis failed: {ai_results['error']}")
            print("Falling back to traditional analysis...")
            use_ai = False
        else:
            print("\n=== AI ANALYSIS RESULTS ===")
            print(ai_results['analysis'])
            print(f"\nAnalysis completed using {ai_results.get('usage', {}).get('total_tokens', 'unknown')} tokens")
            return ai_results
    else:
        print("AI Failed.")


if __name__ == "__main__":
    # Show available weeks
    available_weeks = get_available_weeks()
    if available_weeks:
        print(f"Available weeks: {available_weeks}")
        print(f"Running AI analysis for Week {available_weeks[-1]} (most recent)")
        main(available_weeks[-1], use_ai=True)
    else:
        print("No weekly odds data found. Please run the odds scraper first.")
        print("Running with default Week 1...")
        main(1, use_ai=True)
