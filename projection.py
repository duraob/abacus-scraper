"""
    IMPORTS
"""  
import pandas as pd
import numpy as np
import ast
import os
from datetime import datetime as dt

# Global variable for current week parameter
current_week_param = 0

def load_active_roster(roster_file="data/master_roster.xlsx"):
    """
    Load and clean active roster data from Excel file.
    
    Args:
        roster_file: Path to the master roster Excel file
    
    Returns:
        set: Cleaned set of active player names for filtering
    """
    if not os.path.exists(roster_file):
        raise FileNotFoundError(f"Active roster file not found: {roster_file}")
    
    print(f"Loading active roster from {roster_file}...")
    df_roster = pd.read_excel(roster_file)
    
    # Clean player names by removing common suffixes and extra whitespace
    def clean_player_name(name):
        """Clean player name by removing (IR), (PUP), etc. and normalizing whitespace"""
        if pd.isna(name):
            return None
        
        # Remove common injury/status suffixes
        name = str(name).strip()
        suffixes_to_remove = ['(IR)', '(PUP)', '(NFI)', '(COVID)', '(SUSP)', '(RESERVE)']
        for suffix in suffixes_to_remove:
            name = name.replace(suffix, '').strip()
        
        # Normalize multiple spaces to single space
        name = ' '.join(name.split())
        return name
    
    # Apply cleaning and filter out None values
    df_roster['clean_name'] = df_roster['Player'].apply(clean_player_name)
    active_players = set(df_roster['clean_name'].dropna())
    
    print(f"Loaded {len(active_players)} active players from roster")
    
    # Log any name cleaning that occurred
    original_names = set(df_roster['Player'].dropna())
    if len(original_names) != len(active_players):
        cleaned_count = len(original_names) - len(active_players)
        print(f"Cleaned {cleaned_count} player names (removed injury/status suffixes)")
    
    return active_players

def create_player_team_mapping(roster_file="data/master_roster.xlsx"):
    """
    Create mapping of players to their current team from master roster.
    
    Args:
        roster_file: Path to the master roster Excel file
    
    Returns:
        dict: Mapping of clean player names to their current team abbreviations
    """
    if not os.path.exists(roster_file):
        raise FileNotFoundError(f"Active roster file not found: {roster_file}")
    
    df_roster = pd.read_excel(roster_file)
    
    # Clean player names by removing common suffixes and extra whitespace
    def clean_player_name(name):
        """Clean player name by removing (IR), (PUP), etc. and normalizing whitespace"""
        if pd.isna(name):
            return None
        
        # Remove common injury/status suffixes
        name = str(name).strip()
        suffixes_to_remove = ['(IR)', '(PUP)', '(NFI)', '(COVID)', '(SUSP)', '(RESERVE)']
        for suffix in suffixes_to_remove:
            name = name.replace(suffix, '').strip()
        
        # Normalize multiple spaces to single space
        name = ' '.join(name.split())
        return name
    
    # Apply cleaning and create mapping
    df_roster['clean_name'] = df_roster['Player'].apply(clean_player_name)
    df_roster = df_roster.dropna(subset=['clean_name', 'team_name'])
    
    # Create player to current team mapping
    player_team_mapping = dict(zip(df_roster['clean_name'], df_roster['team_name']))
    
    print(f"Created player-team mapping for {len(player_team_mapping)} players")
    
    return player_team_mapping

def build_team_opponents_schedule(df_game_data):
    """
    Build a team schedule mapping from player-level game data.
    
    Args:
        df_game_data: DataFrame with columns [year, week, home_team, away_team, team, opponent]
    
    Returns:
        DataFrame with columns [team, opps, games] where:
        - team: team name
        - opps: list of opponents played (for schedule strength calculation)
        - games: number of games played
    """
    # Get unique team-game combinations
    team_schedule = df_game_data[['year', 'week', 'home_team', 'away_team', 'team', 'opponent']].drop_duplicates()
    
    # Group by team and aggregate opponents
    team_opponents = team_schedule.groupby('team').agg({
        'opponent': lambda x: str(list(x)),  # String representation of list for CSV compatibility
        'week': 'count'  # Number of games played
    }).rename(columns={'opponent': 'opps', 'week': 'games'})
    
    # Ensure opps is never empty - if no games, use empty list
    team_opponents['opps'] = team_opponents['opps'].apply(
        lambda x: "[]" if pd.isna(x) or x == "0.0" or x == 0.0 else x
    )
    
    return team_opponents

def build_team_statistics(df_game_data):
    """
    Aggregate player-level data to team-level statistics for each game with time weighting.
    
    This function creates both offensive and defensive team statistics:
    - Offensive stats: Direct aggregation of team's offensive performance (time-weighted)
    - Defensive stats: Aggregation of opponent's offensive performance (time-weighted)
                      (represents how well the team's defense performed)
    
    Args:
        df_game_data: DataFrame with player performance data (must include time_weight column)
    
    Returns:
        DataFrame with team-level time-weighted aggregated stats per game
    """
    # Apply time weights to all stats before aggregation
    df_weighted = df_game_data.copy()
    stat_columns = ['pass_cmp', 'pass_att', 'pass_yds', 'pass_tds', 'pass_int', 'sacks',
                   'rush_att', 'rush_yds', 'rush_tds', 'targets', 'receptions', 'rec_yds', 'rec_tds', 'fumbles']
    
    for col in stat_columns:
        df_weighted[col] = df_weighted[col] * df_weighted['time_weight']
    
    # Group by team, opponent, week and aggregate time-weighted offensive stats
    # These represent the team's offensive performance in each game
    team_stats = df_weighted.groupby(['team', 'opponent', 'week']).agg({
        'pass_cmp': 'sum',
        'pass_att': 'sum',
        'pass_yds': 'sum', 
        'pass_tds': 'sum',
        'pass_int': 'sum',
        'sacks': 'sum',
        'rush_att': 'sum',
        'rush_yds': 'sum',
        'rush_tds': 'sum',
        'targets': 'sum',
        'receptions': 'sum',
        'rec_yds': 'sum',
        'rec_tds': 'sum',
        'fumbles': 'sum'
    }).reset_index()
    
    # Calculate defensive stats by aggregating opponent's offensive performance with time weighting
    # When we group by opponent, we're getting the opponent's offensive stats
    # These become our defensive stats (how well we defended against them)
    opponent_offensive_stats = df_weighted.groupby(['opponent', 'team', 'week']).agg({
        'pass_cmp': 'sum',
        'pass_att': 'sum',
        'pass_yds': 'sum',
        'pass_tds': 'sum', 
        'pass_int': 'sum',
        'sacks': 'sum',
        'rush_att': 'sum',
        'rush_yds': 'sum',
        'rush_tds': 'sum',
        'targets': 'sum',
        'receptions': 'sum',
        'rec_yds': 'sum',
        'rec_tds': 'sum',
        'fumbles': 'sum'
    }).reset_index()
    
    # Custom mapping: Opponent's offensive stats become our defensive stats
    # This represents how well our defense performed against the opponent's offense
    def_col_mapping = {
        'pass_cmp': 'def_pass_cmp',      # Opponent pass completions = our defensive pass completions allowed
        'pass_att': 'def_pass_att',      # Opponent pass attempts = our defensive pass attempts allowed
        'pass_yds': 'def_pass_yd',       # Opponent pass yards = our defensive pass yards allowed
        'pass_tds': 'def_pass_td',       # Opponent pass TDs = our defensive pass TDs allowed
        'pass_int': 'def_int',           # Opponent interceptions = our defensive interceptions allowed
        'sacks': 'def_sacks',            # Opponent sacks = our defensive sacks allowed
        'rush_att': 'def_rush_att',      # Opponent rush attempts = our defensive rush attempts allowed
        'rush_yds': 'def_rush_yd',       # Opponent rush yards = our defensive rush yards allowed
        'rush_tds': 'def_rush_td',       # Opponent rush TDs = our defensive rush TDs allowed
        'targets': 'def_targets',        # Opponent targets = our defensive targets allowed
        'receptions': 'def_rec',         # Opponent receptions = our defensive receptions allowed
        'rec_yds': 'def_rec_yd',         # Opponent receiving yards = our defensive receiving yards allowed
        'rec_tds': 'def_rec_td',         # Opponent receiving TDs = our defensive receiving TDs allowed
        'fumbles': 'def_fum'             # Opponent fumbles = our defensive fumbles allowed
    }
    
    # Rename opponent offensive columns to defensive columns using the custom mapping
    opponent_offensive_stats.columns = ['team', 'opponent', 'week'] + [def_col_mapping[col] for col in opponent_offensive_stats.columns[3:]]
    
    # Merge offensive and defensive stats
    # Now each team has both their offensive performance and their defensive performance
    team_complete = pd.merge(team_stats, opponent_offensive_stats, on=['team', 'opponent', 'week'], how='outer')
    
    return team_complete

def determine_next_opponent(team, current_week, df_schedule):
    """
    Determine the next opponent for a team based on current week and schedule.
    
    Args:
        team: Team name
        current_week: Current week number
        df_schedule: Schedule DataFrame with columns [Round Number, Away Team, Home Team]
    
    Returns:
        Next opponent team name or None if on bye
    """
    # Find next game for this team (week > current_week)
    future_games = df_schedule[df_schedule['Round Number'] > current_week]
    
    # Find games where this team plays
    team_games = future_games[
        (future_games['Away Team'] == team) | 
        (future_games['Home Team'] == team)
    ]
    
    if team_games.empty:
        return None  # Team is on bye or no more games
    
    # Get the next game (lowest week number)
    next_game = team_games.loc[team_games['Round Number'].idxmin()]
    
    # Determine opponent
    if next_game['Away Team'] == team:
        return next_game['Home Team']
    else:
        return next_game['Away Team']

def create_time_weighted_dataset(week_2025_file, weeks_2024_file, target_weeks_2024):
    """
    Merge 2025 Week 1 with specified 2024 weeks, applying time decay weighting.
    
    Time weights: 2025 Week 1 = 1.0, 2024 Week 17 = 0.9, ..., 2024 Week 9 = 0.1
    This ensures recent games have higher influence on projections.
    
    Args:
        week_2025_file: Path to 2025 Week 1 data (highest weight)
        weeks_2024_file: Path to 2024 season data
        target_weeks_2024: List of 2024 weeks to include (e.g., [9,10,11,12,13,14,15,16,17])
    
    Returns:
        DataFrame with time-weighted game data including weight column
    """
    print(f"Loading 2025 Week 1 data from {week_2025_file}...")
    df_2025 = pd.read_csv(week_2025_file)
    
    print(f"Loading 2024 data from {weeks_2024_file}...")
    df_2024 = pd.read_csv(weeks_2024_file)
    
    # Filter 2024 data to target weeks
    df_2024_filtered = df_2024[df_2024['week'].isin(target_weeks_2024)].copy()
    print(f"Filtered 2024 data to weeks {target_weeks_2024}: {len(df_2024_filtered)} records")
    
    # Normalize team names to abbreviations for consistency
    # 2025 data has full team names in opponent column, 2024 data uses abbreviations
    team_name_mapping = {
        'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL', 'Carolina Panthers': 'CAR',
        'Chicago Bears': 'CHI', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
        'Detroit Lions': 'DET', 'Houston Texans': 'HOU', 'Kansas City Chiefs': 'KAN',
        'Miami Dolphins': 'MIA', 'New England Patriots': 'NWE', 'New Orleans Saints': 'NOR',
        'New York Giants': 'NYG', 'New York Jets': 'NYJ', 'Seattle Seahawks': 'SEA',
        'Tennessee Titans': 'TEN'
    }
    
    # Normalize opponent column in 2025 data to use abbreviations
    df_2025['opponent'] = df_2025['opponent'].map(team_name_mapping).fillna(df_2025['opponent'])
    
    # Add time weights
    df_2025['time_weight'] = 1.0  # Most recent, highest weight
    
    # Calculate time weights for 2024 weeks (0.9 down to 0.1)
    weight_map = {}
    for i, week in enumerate(sorted(target_weeks_2024, reverse=True)):
        weight_map[week] = 0.9 - (i * 0.1)
    
    df_2024_filtered['time_weight'] = df_2024_filtered['week'].map(weight_map)
    
    # Combine datasets
    df_combined = pd.concat([df_2025, df_2024_filtered], ignore_index=True)
    
    print(f"Combined dataset: {len(df_combined)} total records")
    print(f"Time weights applied: 2025 Week 1 = 1.0, 2024 weeks = {weight_map}")
    print(f"Team names normalized to abbreviations for consistency")
    
    return df_combined

def create_time_weighted_dataset_dynamic(week_2025_file, weeks_2024_file, target_weeks_2024, projection_week):
    """
    Create time-weighted dataset based on projection week requirements.
    
    Args:
        week_2025_file: Path to 2025 season data
        weeks_2024_file: Path to 2024 season data  
        target_weeks_2024: List of 2024 weeks to include as fallback
        projection_week: Week number for projections (1 = Week 1, 2 = Week 2, etc.)
    
    Returns:
        DataFrame with time-weighted game data including weight column
    """
    print(f"Loading 2025 data from {week_2025_file}...")
    df_2025 = pd.read_csv(week_2025_file)
    
    print(f"Loading 2024 data from {weeks_2024_file}...")
    df_2024 = pd.read_csv(weeks_2024_file)
    
    # Determine data selection based on projection week
    if projection_week == 1:
        # Week 1 projections: Use 10 games from 2024 (no 2025 data yet)
        print("Week 1 projections: Using 10 games from 2024 data")
        weeks_to_include_2025 = []
        weeks_to_include_2024 = sorted(target_weeks_2024, reverse=True)[:10]  # Most recent 10 weeks
        df_2025_filtered = pd.DataFrame()  # Empty DataFrame
        df_2024_filtered = df_2024[df_2024['week'].isin(weeks_to_include_2024)].copy()
        
    elif projection_week == 2:
        # Week 2 projections: Use 9 games from 2024 + 1 game from 2025
        print("Week 2 projections: Using 9 games from 2024 + 1 game from 2025")
        available_2025_weeks = sorted(df_2025['week'].unique())
        weeks_to_include_2025 = [available_2025_weeks[0]]  # First week of 2025
        weeks_to_include_2024 = sorted(target_weeks_2024, reverse=True)[:9]  # Most recent 9 weeks
        df_2025_filtered = df_2025[df_2025['week'].isin(weeks_to_include_2025)].copy()
        df_2024_filtered = df_2024[df_2024['week'].isin(weeks_to_include_2024)].copy()
        
    else:
        # Week 3+ projections: Use available 2025 weeks + fill remaining with 2024
        print(f"Week {projection_week} projections: Using available 2025 weeks + 2024 fill")
        available_2025_weeks = sorted(df_2025['week'].unique())
        weeks_to_include_2025 = [w for w in available_2025_weeks if w < projection_week]
        weeks_needed_from_2024 = 10 - len(weeks_to_include_2025)
        weeks_to_include_2024 = sorted(target_weeks_2024, reverse=True)[:weeks_needed_from_2024]
        df_2025_filtered = df_2025[df_2025['week'].isin(weeks_to_include_2025)].copy()
        df_2024_filtered = df_2024[df_2024['week'].isin(weeks_to_include_2024)].copy()
    
    print(f"Including 2025 weeks: {weeks_to_include_2025}")
    print(f"Including 2024 weeks: {weeks_to_include_2024}")
    
    # Normalize team names to abbreviations for consistency
    team_name_mapping = {
        'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL', 'Carolina Panthers': 'CAR',
        'Chicago Bears': 'CHI', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
        'Detroit Lions': 'DET', 'Houston Texans': 'HOU', 'Kansas City Chiefs': 'KAN',
        'Miami Dolphins': 'MIA', 'New England Patriots': 'NWE', 'New Orleans Saints': 'NOR',
        'New York Giants': 'NYG', 'New York Jets': 'NYJ', 'Seattle Seahawks': 'SEA',
        'Tennessee Titans': 'TEN'
    }
    
    # Normalize opponent column in 2025 data to use abbreviations (only if data exists)
    if not df_2025_filtered.empty:
        df_2025_filtered['opponent'] = df_2025_filtered['opponent'].map(team_name_mapping).fillna(df_2025_filtered['opponent'])
    
    # Calculate time weights - most recent week gets highest weight
    all_weeks = []
    weight_map = {}
    
    # Add 2025 weeks with weights (most recent = 1.0)
    if not df_2025_filtered.empty:
        for i, week in enumerate(sorted(weeks_to_include_2025, reverse=True)):
            weight_map[('2025', week)] = 1.0 - (i * 0.1)
            all_weeks.append(('2025', week))
    
    # Add 2024 weeks with weights (continuing the decay)
    if not df_2024_filtered.empty:
        start_weight = 1.0 - (len(weeks_to_include_2025) * 0.1)
        for i, week in enumerate(sorted(weeks_to_include_2024, reverse=True)):
            weight_map[('2024', week)] = start_weight - (i * 0.1)
            all_weeks.append(('2024', week))
    
    # Apply weights
    if not df_2025_filtered.empty:
        df_2025_filtered['time_weight'] = df_2025_filtered['week'].apply(lambda w: weight_map[('2025', w)])
    
    if not df_2024_filtered.empty:
        df_2024_filtered['time_weight'] = df_2024_filtered['week'].apply(lambda w: weight_map[('2024', w)])
    
    # Combine datasets
    if not df_2024_filtered.empty:
        df_combined = pd.concat([df_2025_filtered, df_2024_filtered], ignore_index=True)
    else:
        df_combined = df_2025_filtered.copy()
    
    print(f"Combined dataset: {len(df_combined)} total records")
    print(f"Time weights applied: {weight_map}")
    print(f"Team names normalized to abbreviations for consistency")
    
    return df_combined

def create_team_dataset_from_game_data(df_game_data, df_schedule=None, current_week=None):
    """
    Create a complete team dataset from player-level game data with time weighting.
    
    This function creates team-level statistics by:
    1. Aggregating each team's offensive performance across all games (with time weights)
    2. Aggregating each team's defensive performance (opponent offensive stats) across all games (with time weights)
    3. Adding schedule information for strength of schedule calculations
    
    Args:
        df_game_data: DataFrame with player performance data (must include time_weight column)
        df_schedule: Schedule DataFrame with columns [Week, away_team, home_team] (optional)
        current_week: Current week number for determining next opponent (optional)
    
    Returns:
        DataFrame with team-level data including opps column and time-weighted aggregated stats
    """
    # Build team opponents schedule
    team_schedule = build_team_opponents_schedule(df_game_data)
    
    # Build team statistics
    team_stats = build_team_statistics(df_game_data)
    
    # Aggregate team stats across all games (sum all stats)
    team_aggregated = team_stats.groupby('team').agg({
        'pass_cmp': 'sum',
        'pass_att': 'sum',
        'pass_yds': 'sum',
        'pass_tds': 'sum',
        'pass_int': 'sum',
        'sacks': 'sum',
        'rush_att': 'sum',
        'rush_yds': 'sum',
        'rush_tds': 'sum',
        'targets': 'sum',
        'receptions': 'sum',
        'rec_yds': 'sum',
        'rec_tds': 'sum',
        'fumbles': 'sum',
        'def_pass_cmp': 'sum',
        'def_pass_att': 'sum',
        'def_pass_yd': 'sum',
        'def_pass_td': 'sum',
        'def_int': 'sum',
        'def_sacks': 'sum',
        'def_rush_att': 'sum',
        'def_rush_yd': 'sum',
        'def_rush_td': 'sum',
        'def_targets': 'sum',
        'def_rec': 'sum',
        'def_rec_yd': 'sum',
        'def_rec_td': 'sum',
        'def_fum': 'sum'
    }).reset_index()
    
    # Rename columns to match analyze function expectations exactly
    team_aggregated = team_aggregated.rename(columns={
        'pass_yds': 'pass_yd',
        'pass_tds': 'pass_td',
        'rush_yds': 'rush_yd',
        'rush_tds': 'rush_td',
        'rec_yds': 'rec_yd',
        'rec_tds': 'rec_td',
        'receptions': 'rec',
        'fumbles': 'off_fum'
    })
    
    # Merge with team schedule to get opps and games
    team_complete = pd.merge(team_aggregated, team_schedule, on='team', how='left')
    
    # Add next opponent if schedule data is provided
    if df_schedule is not None and current_week is not None:
        team_complete['next_op'] = team_complete['team'].apply(
            lambda team: determine_next_opponent(team, current_week, df_schedule)
        )
    else:
        team_complete['next_op'] = None
    
    # Data validation: Remove any rows with invalid team names
    team_complete = team_complete[team_complete['team'].notna()]
    team_complete = team_complete[team_complete['team'] != '']
    team_complete = team_complete[team_complete['team'] != 0.0]
    
    print(f"Final team dataset size: {len(team_complete)} teams")
    
    # Keep team as a regular column - let analyze function handle index management
    return team_complete

def create_player_dataset_from_game_data(df_game_data, active_roster, player_team_mapping):
    """
    Create a player dataset from player-level game data with time weighting.
    Only includes players on the active roster, consolidated by their current team.
    
    Args:
        df_game_data: DataFrame with player performance data (must include time_weight column)
        active_roster: Set of active player names for filtering
        player_team_mapping: Dict mapping player names to their current team
    
    Returns:
        DataFrame with player-level time-weighted aggregated stats for active players only, consolidated by current team
    """
    # Log initial statistics
    total_players_in_data = df_game_data['player'].nunique()
    print(f"Total players in game data: {total_players_in_data}")
    print(f"Active roster size: {len(active_roster)}")
    
    # Filter game data to only include active players
    df_filtered = df_game_data[df_game_data['player'].isin(active_roster)].copy()
    active_players_found = df_filtered['player'].nunique()
    
    print(f"Active players found in game data: {active_players_found}")
    
    # Log players in game data but not on active roster (investigation needed)
    players_in_data = set(df_game_data['player'].unique())
    players_not_on_roster = players_in_data - active_roster
    if players_not_on_roster:
        print(f"WARNING: {len(players_not_on_roster)} players in game data but not on active roster:")
        for player in sorted(list(players_not_on_roster)[:10]):  # Show first 10
            print(f"  - {player}")
        if len(players_not_on_roster) > 10:
            print(f"  ... and {len(players_not_on_roster) - 10} more")
    
    # Log players on active roster but not in game data (expected for some positions)
    players_not_in_data = active_roster - players_in_data
    if players_not_in_data:
        print(f"INFO: {len(players_not_in_data)} players on active roster but not in game data (expected for some positions)")
    
    if df_filtered.empty:
        raise ValueError("No active players found in game data. Check name matching between roster and game data.")
    
    # Apply time weights to all stats before aggregation
    df_filtered_weighted = df_filtered.copy()
    stat_columns = ['pass_cmp', 'pass_att', 'pass_yds', 'pass_tds', 'pass_int', 'sacks',
                   'rush_att', 'rush_yds', 'rush_tds', 'targets', 'receptions', 'rec_yds', 'rec_tds', 'fumbles']
    
    for col in stat_columns:
        df_filtered_weighted[col] = df_filtered_weighted[col] * df_filtered_weighted['time_weight']
    
    # Group by player only (not by team) to consolidate all team performances
    player_stats = df_filtered_weighted.groupby('player').agg({
        'pass_cmp': 'sum',
        'pass_att': 'sum',
        'pass_yds': 'sum',
        'pass_tds': 'sum',
        'pass_int': 'sum',
        'sacks': 'sum',
        'rush_att': 'sum',
        'rush_yds': 'sum',
        'rush_tds': 'sum',
        'targets': 'sum',
        'receptions': 'sum',
        'rec_yds': 'sum',
        'rec_tds': 'sum',
        'fumbles': 'sum'
    }).reset_index()
    
    # Rename columns to match analyze function expectations exactly
    player_stats = player_stats.rename(columns={
        'pass_yds': 'pass_yd',
        'pass_tds': 'pass_td',
        'rush_yds': 'rush_yd',
        'rush_tds': 'rush_td',
        'rec_yds': 'rec_yd',
        'rec_tds': 'rec_td',
        'receptions': 'rec',
        'fumbles': 'fum',
        'targets': 'tar'
    })
    
    # Count total games played (weeks) for each player across all teams
    games_played = df_filtered.groupby('player')['week'].nunique().reset_index()
    games_played.columns = ['player', 'g']
    
    # Merge stats with games played
    player_complete = pd.merge(player_stats, games_played, on='player', how='left')
    
    # Add current team from mapping
    player_complete['team'] = player_complete['player'].map(player_team_mapping)
    
    # Remove players without current team mapping (shouldn't happen with active roster)
    player_complete = player_complete.dropna(subset=['team'])
    
    # Rename player column to 'name' to match expected format
    player_complete.rename(columns={'player': 'name'}, inplace=True)
    
    # Data validation: Remove any rows with invalid team names
    player_complete = player_complete[player_complete['team'].notna()]
    player_complete = player_complete[player_complete['team'] != '']
    player_complete = player_complete[player_complete['team'] != 0.0]
    
    print(f"Final player dataset size: {len(player_complete)} players (consolidated by current team)")
    
    # Keep name as a regular column - let analyze function handle index management
    return player_complete

def analyze(df_team, df_players, projection_week=1):
    """
        SETUP DATAFRAMES
            Fill any empty cells
            Determine Number of Games Played By Each Team's Schedule
    """
    df_team = df_team.fillna(0.0)
    df_players = df_players.fillna(0.0)
    df_team_avg = df_team.copy()
    df_team_avg.set_index("team", inplace=True)
    df_team_avg.index.name="team"
    # Handle NaN values in opps column before applying literal_eval
    df_team_avg['opps'] = df_team_avg['opps'].fillna("[]")
    # Also handle any 0.0 values that might have been created
    df_team_avg['opps'] = df_team_avg['opps'].replace(0.0, "[]")
    df_team_avg['opps'] = df_team_avg['opps'].apply(ast.literal_eval)
    df_team_avg['games'] = df_team_avg['opps'].apply(len)

    """
      LEAGUE SUMS - 
        We will want to compare each team to the league average
        Based on position against league average we can normalize our projections w/ matchup strength
    """
    num_games = df_team_avg["games"].sum()
    num_rush_att = df_team_avg["rush_att"].sum()
    num_pass_att = df_team_avg["pass_att"].sum()
    num_def_rush_att = df_team_avg["def_rush_att"].sum()
    num_def_pass_att = df_team_avg["def_pass_att"].sum()

    # CALCULATE LEAGUE ATT AVG
    avg_dict = {}
    avg_dict["league"] = [
        df_team_avg["pass_cmp"].sum() / num_games,
        df_team_avg["pass_att"].sum() / num_games,
                          df_team_avg["pass_yd"].sum() / num_pass_att,
                          df_team_avg["pass_td"].sum() / num_pass_att,
                          df_team_avg["pass_int"].sum() / num_pass_att,
        df_team_avg["sacks"].sum() / num_games,
                          df_team_avg["rush_att"].sum() / num_games,
                          df_team_avg["rush_yd"].sum() / num_rush_att,
                          df_team_avg["rush_td"].sum() / num_rush_att,
        df_team_avg["targets"].sum() / num_pass_att,
        df_team_avg["rec"].sum() / num_pass_att,
                          df_team_avg["rec_yd"].sum() / num_pass_att,
                          df_team_avg["rec_td"].sum() / num_pass_att,
                          df_team_avg["off_fum"].sum() / (num_pass_att + num_rush_att),
        df_team_avg["def_pass_cmp"].sum() / num_games,
                          df_team_avg["def_pass_att"].sum() / num_games,
                          df_team_avg["def_pass_yd"].sum() / num_def_pass_att,
                          df_team_avg["def_pass_td"].sum() / num_def_pass_att,
                          df_team_avg["def_int"].sum() / num_def_pass_att,
        df_team_avg["def_sacks"].sum() / num_games,
                          df_team_avg["def_rush_att"].sum() / num_games,
                          df_team_avg["def_rush_yd"].sum() / num_def_rush_att,
                          df_team_avg["def_rush_td"].sum() / num_def_rush_att,
        df_team_avg["def_targets"].sum() / num_def_pass_att,
        df_team_avg["def_rec"].sum() / num_def_pass_att,
                          df_team_avg["def_rec_yd"].sum() / num_def_pass_att,
                          df_team_avg["def_rec_td"].sum() / num_def_pass_att,
                          df_team_avg["def_fum"].sum() / (num_def_pass_att + num_def_rush_att)]
    df_leag_avg = pd.DataFrame.from_dict(avg_dict, orient="index", columns=[(df_team_avg.columns)[0:28]])

    # CALCULATE AVG TEAM STAT PER ATT - Fantasy is largely dependent on attempts made by player & opportunity provided by teams

    # PASSING
    df_team_avg['pass_cmp'] = df_team_avg['pass_cmp'] / df_team_avg['pass_att']
    df_team_avg['pass_yd'] = df_team_avg['pass_yd'] / df_team_avg['pass_att']
    df_team_avg['pass_td'] = df_team_avg['pass_td'] / df_team_avg['pass_att']
    df_team_avg['pass_int'] = df_team_avg['pass_int'] / df_team_avg['pass_att']
    df_team_avg['sacks'] = df_team_avg['sacks'] / df_team_avg['games']
    # RUSHING
    df_team_avg['rush_att'] = df_team_avg["rush_att"] / df_team_avg['games']
    df_team_avg['rush_yd'] = df_team_avg["rush_yd"] / df_team_avg['rush_att'].replace(0, 0.0001)
    df_team_avg['rush_td'] = df_team_avg["rush_td"] / df_team_avg['rush_att'].replace(0, 0.0001)
    # RECEIVING
    df_team_avg['targets'] = df_team_avg["targets"] / df_team_avg['pass_att'].replace(0, 0.0001)
    df_team_avg['rec'] = df_team_avg["rec"] / df_team_avg['targets'].replace(0, 0.0001)
    df_team_avg['rec_yd'] = df_team_avg["rec_yd"] / df_team_avg['pass_att'].replace(0, 0.0001)
    df_team_avg['rec_td'] = df_team_avg["rec_td"] / df_team_avg['pass_att'].replace(0, 0.0001)
    df_team_avg['off_fum'] = df_team_avg["off_fum"] / (df_team_avg['pass_att'] + df_team_avg['rush_att']).replace(0, 0.0001)
    # OFF ATT
    df_team_avg['pass_att'] = df_team_avg["pass_att"] / df_team_avg['games']
    df_team_avg['rush_att'] = df_team_avg["rush_att"] / df_team_avg['games']

    # DEF PASSING
    df_team_avg['def_pass_cmp'] = df_team_avg['def_pass_cmp'] / df_team_avg['def_pass_att'].replace(0, 0.0001)
    df_team_avg['def_pass_yd'] = df_team_avg['def_pass_yd'] / df_team_avg['def_pass_att'].replace(0, 0.0001)
    df_team_avg['def_pass_td'] = df_team_avg['def_pass_td'] / df_team_avg['def_pass_att'].replace(0, 0.0001)
    df_team_avg['def_int'] = df_team_avg['def_int'] / df_team_avg['def_pass_att'].replace(0, 0.0001)
    df_team_avg['def_sacks'] = df_team_avg['def_sacks'] / df_team_avg['games']
    # DEF RUSHING
    df_team_avg['def_rush_yd'] = df_team_avg["def_rush_yd"] / df_team_avg['def_rush_att'].replace(0, 0.0001)
    df_team_avg['def_rush_td'] = df_team_avg["def_rush_td"] / df_team_avg['def_rush_att'].replace(0, 0.0001)
    # DEF RECEIVING
    df_team_avg['def_targets'] = df_team_avg["def_targets"] / df_team_avg['def_pass_att'].replace(0, 0.0001)
    df_team_avg['def_rec'] = df_team_avg["def_rec"] / df_team_avg['def_pass_att'].replace(0, 0.0001)
    df_team_avg['def_rec_yd'] = df_team_avg["def_rec_yd"] / df_team_avg['def_pass_att'].replace(0, 0.0001)
    df_team_avg['def_rec_td'] = df_team_avg["def_rec_td"] / df_team_avg['def_pass_att'].replace(0, 0.0001)
    df_team_avg['def_fum'] = df_team_avg["def_fum"] / (df_team_avg['def_pass_att'] + df_team_avg['def_rush_att']).replace(0, 0.0001)
    # DEF ATT
    df_team_avg['def_pass_att'] = df_team_avg["def_pass_att"] / df_team_avg['games']
    df_team_avg['def_rush_att'] = df_team_avg["def_rush_att"] / df_team_avg['games']
    
    # Clean up team statistics calculations - replace any NaN or infinite values with 0
    df_team_avg = df_team_avg.replace([np.inf, -np.inf], 0)
    df_team_avg = df_team_avg.fillna(0)

    # CALCULATE TEAM RATIOS TO LEAGUE ATT AVG
    
    # Offense Stats in first 29 cols - Comparison of Each Team in the League against League Avg
    for col in (df_team_avg.columns)[0:28]:
        stat = df_leag_avg.loc["league", col]
        # Prevent divide by zero - replace 0 with 0.0001 to avoid infinite values
        stat_value = stat.values[0] if stat.values[0] != 0 else 0.0001
        df_team_avg[f"ratio_{col}"] = df_team_avg[col] / stat_value
    
    # Clean up any infinite values that may have been created
    df_team_avg = df_team_avg.replace([np.inf, -np.inf], 0)

    # CALCULATE SCHEDULE STRENGTH PER STAT - Comparison of Each Team in the League agsinst League Avg
    for col in (df_team_avg.columns)[31:59]:
        df_team_avg[f"schedstr_{col}"] = df_team_avg.apply(lambda row: calc_matchup_str(row, col, df_team_avg), axis=1)
    
    # Clean up schedule strength calculations - replace any NaN or infinite values with 0
    df_team_avg = df_team_avg.fillna(0)
    df_team_avg = df_team_avg.replace([np.inf, -np.inf], 0)

    """
        PLAYERS DATA
    """
    # SETUP DATA
    df_player_avg = df_players.copy()
    df_player_avg.set_index("name", inplace=True)
    df_player_avg.index.name="name"
    num_games = df_player_avg["g"].sum()

    # CALCULATE AVERAGE PLAYER STAT PER ATT
    # PASS
    df_player_avg["pass_cmp"] = df_player_avg["pass_cmp"] / df_player_avg["pass_att"].replace(0, 0.0001)
    df_player_avg["pass_yd"] = df_player_avg["pass_yd"] / df_player_avg["pass_att"].replace(0, 0.0001)
    df_player_avg["pass_td"] = df_player_avg["pass_td"] / df_player_avg["pass_att"].replace(0, 0.0001)
    df_player_avg["pass_int"] = df_player_avg["pass_int"] / df_player_avg["pass_att"].replace(0, 0.0001)
    # RUSH
    df_player_avg["rush_yd"] = df_player_avg["rush_yd"] / df_player_avg["rush_att"].replace(0, 0.0001)
    df_player_avg["rush_td"] = df_player_avg["rush_td"] / df_player_avg["rush_att"].replace(0, 0.0001)
    # REC
    df_player_avg["rec"] = df_player_avg["rec"] / df_player_avg["tar"].replace(0, 0.0001)
    df_player_avg["rec_yd"] = df_player_avg["rec_yd"] / df_player_avg["tar"].replace(0, 0.0001)
    df_player_avg["rec_td"] = df_player_avg["rec_td"] / df_player_avg["tar"].replace(0, 0.0001)
    df_player_avg["fum"] = df_player_avg["fum"] / (df_player_avg["tar"] + df_player_avg["rush_att"]).replace(0, 0.0001)
    # ATTS
    df_player_avg["tar"] = df_player_avg["tar"] / df_player_avg["g"].replace(0, 0.0001)
    df_player_avg["pass_att"] = df_player_avg["pass_att"] / df_player_avg["g"].replace(0, 0.0001)
    df_player_avg["rush_att"] = df_player_avg["rush_att"] / df_player_avg["g"].replace(0, 0.0001)
    
    # Clean up any infinite values that may have been created
    df_player_avg = df_player_avg.replace([np.inf, -np.inf], 0)
    df_player_avg = df_player_avg.fillna(0)

    # CALCULATE PLAYER CORE STRENGTH STATS
    # Core Strength - Baseline Stats from a Player Based on Attempts & Strength of Schedule
    # Ex. Normalize Data by Taking Average Pass Attempts from the Player, Compare this to the Avg Pass Attempts of the League...
    # ...if the player has been attempting less pass attempts but have been facing the best NFL defenses then their actual average against the "league average team"...
    # ...can be predicted to be higher than their current stats
    df_player_proj = df_player_avg.copy().round(2)
    df_player_proj["core_pass_att"] = df_player_proj.apply(lambda row: (row["pass_att"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_pass_att"]), axis=1)
    df_player_proj["core_rush_att"] = df_player_proj.apply(lambda row: (row["rush_att"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rush_att"]), axis=1)
    df_player_proj["core_tar"] = df_player_proj.apply(lambda row: (row["tar"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_pass_att"]), axis=1)

    df_player_proj["core_pass_yd"] = df_player_proj.apply(lambda row: (row["core_pass_att"]) * (row["pass_yd"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_pass_yd"]), axis=1)
    df_player_proj["core_pass_td"] = df_player_proj.apply(lambda row: (row["core_pass_att"]) * (row["pass_td"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_pass_td"]), axis=1)
    df_player_proj["core_int"] = df_player_proj.apply(lambda row: (row["core_pass_att"]) * (row["pass_int"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_int"]), axis=1)
    df_player_proj["core_rush_yd"] = df_player_proj.apply(lambda row: (row["core_rush_att"]) * (row["rush_yd"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rush_yd"]), axis=1)
    df_player_proj["core_rush_td"] = df_player_proj.apply(lambda row: (row["core_rush_att"]) * (row["rush_td"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rush_td"]), axis=1)
    df_player_proj["core_rec"] = df_player_proj.apply(lambda row: (row["core_tar"]) * (row["rec"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rec"]) , axis=1)
    df_player_proj["core_rec_yd"] = df_player_proj.apply(lambda row: (row["core_tar"]) * (row["rec_yd"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rec_yd"]), axis=1)
    df_player_proj["core_rec_td"] = df_player_proj.apply(lambda row: (row["core_tar"]) * (row["rec_td"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rec_td"]), axis=1)
    df_player_proj["core_fum"] = df_player_proj.apply(lambda row: (row["core_tar"] + row["core_rush_att"]) * (row["fum"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_fum"]), axis=1)
    
    # Clean up core strength calculations - replace any NaN or infinite values with 0
    df_player_proj = df_player_proj.replace([np.inf, -np.inf], 0)
    df_player_proj = df_player_proj.fillna(0)
    
    
    # CALCULATE PLAYER PROJ STRENGTH STATS
    # Based on the core strength of a player, looking ahead to next game and how that team does against league average project the amount of stats
    # If a player's run strength is above league average and they are playing a low ranking rush defense, we will estimate them at a higher projection.
    
    def safe_get_opponent_ratio(row, stat_name):
        """Safely get opponent ratio, handling missing or invalid next_op values"""
        try:
            next_opponent = df_team_avg.loc[row["team"], "next_op"]
            if pd.isna(next_opponent) or next_opponent == 0.0 or next_opponent == '':
                return 1.0  # Default to league average if no opponent
            return df_team_avg.loc[next_opponent, stat_name]
        except (KeyError, TypeError):
            return 1.0  # Default to league average if lookup fails
    
    df_player_proj["proj_pass_att"] = df_player_proj.apply(lambda row: (row["core_pass_att"]) * safe_get_opponent_ratio(row, "ratio_def_pass_att"), axis=1)
    df_player_proj["proj_rush_att"] = df_player_proj.apply(lambda row: (row["core_rush_att"]) * safe_get_opponent_ratio(row, "ratio_def_rush_att"), axis=1)
    df_player_proj["proj_tar"] = df_player_proj.apply(lambda row: (row["core_tar"]) * safe_get_opponent_ratio(row, "ratio_def_pass_att"), axis=1)

    df_player_proj["proj_pass_yd"] = df_player_proj.apply(lambda row: (row["proj_pass_att"]) * (row["pass_yd"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_pass_yd"]) * safe_get_opponent_ratio(row, "ratio_def_pass_yd"), axis=1)
    df_player_proj["proj_pass_td"] = df_player_proj.apply(lambda row: (row["proj_pass_att"]) * (row["pass_td"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_pass_td"]) * safe_get_opponent_ratio(row, "ratio_def_pass_td"), axis=1)
    df_player_proj["proj_int"] = df_player_proj.apply(lambda row: (row["proj_pass_att"]) * (row["pass_int"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_int"]) * safe_get_opponent_ratio(row, "ratio_def_int"), axis=1)
    df_player_proj["proj_rush_yd"] = df_player_proj.apply(lambda row: (row["proj_rush_att"]) * (row["rush_yd"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rush_yd"]) * safe_get_opponent_ratio(row, "ratio_def_rush_yd"), axis=1)
    df_player_proj["proj_rush_td"] = df_player_proj.apply(lambda row: (row["proj_rush_att"]) * (row["rush_td"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rush_td"]) * safe_get_opponent_ratio(row, "ratio_def_rush_td"), axis=1)
    df_player_proj["proj_rec"] = df_player_proj.apply(lambda row: (row["proj_tar"]) * (row["rec"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rec"]) * safe_get_opponent_ratio(row, "ratio_def_rec"), axis=1)
    df_player_proj["proj_rec_yd"] = df_player_proj.apply(lambda row: (row["proj_tar"]) * (row["rec_yd"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rec_yd"]) * safe_get_opponent_ratio(row, "ratio_def_rec_yd"), axis=1)
    df_player_proj["proj_rec_td"] = df_player_proj.apply(lambda row: (row["proj_tar"]) * (row["rec_td"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_rec_td"]) * safe_get_opponent_ratio(row, "ratio_def_rec_td"), axis=1)
    df_player_proj["proj_fum"] = df_player_proj.apply(lambda row: (row["proj_tar"] + row["proj_rush_att"]) * (row["fum"] / df_team_avg.loc[row["team"], "schedstr_ratio_def_fum"]) * safe_get_opponent_ratio(row, "def_fum"), axis=1)
    
    # Final cleanup - replace any NaN or infinite values with 0 before rounding
    df_player_proj = df_player_proj.replace([np.inf, -np.inf], 0)
    df_player_proj = df_player_proj.fillna(0)
    
    # Round and save
    df_round = df_player_proj.round(2)
    
    # Create projections directory if it doesn't exist
    import os
    projections_dir = "data/projections"
    os.makedirs(projections_dir, exist_ok=True)
    
    # Generate filename based on projection week
    filename = f"nfl25_proj_week{projection_week}.csv"
    filepath = os.path.join(projections_dir, filename)
    
    df_round.to_csv(filepath, index="name")
    print(f"Saved projections to: {filepath}")

def calc_matchup_str(row, stat, df):
    """
        Based on amount of games played determine matchup strength
        Need to locate team and find their DEFENSE stats against the players off stats
    """
    stat_agg = 0
    for team in row["opps"]:
        stat_agg = stat_agg + df.loc[team, stat]
    
    # Prevent divide by zero - if no games played, return 0
    if row["games"] == 0:
        return 0
    
    return stat_agg / row["games"]

def run():
    """
        Main Program Tasks:
            CALCULATE SCHEDULE STRENGTH STATS
            CALCULATE CORE STR OF PLAYERS
            CALCULATE MATCHUP STR
            INTAKE PLAYER SALARIES
            CALCULATE PLAYER VALUES.. POINTS PER DOLLAR
    """
    start = dt.now()
    print(f"\nProjection Program Start - {start}:\n")
    
    # Try to load existing team and player data first
    try:
        df_team = pd.read_csv("nfl25_team.csv", index_col=0)
        df_players = pd.read_csv("nfl25_players.csv", index_col=0)
        print("Loaded existing team and player data files")
    except FileNotFoundError:
        print("Existing data files not found. Please run with game data to create new datasets.")
        return
    
    end = dt.now()
    print(f"\nProjection Program End - {end}\n Total: {end - start}\n")

    analyze(df_team, df_players)

def run_with_time_weighted_data(week_2025_file, weeks_2024_file, target_weeks_2024, 
                               schedule_file=None, current_week=None, roster_file="data/master_roster.xlsx"):
    """
    Run the projection engine using time-weighted last 10 games with dynamic week progression.
    Only includes players on the active roster to eliminate noise from inactive players.
    
    Time weights: Most recent week = 1.0, previous weeks = 0.9, 0.8, ..., 0.1
    This ensures recent games have higher influence on projections.
    
    Args:
        week_2025_file: Path to 2025 season data (e.g., 'data/game_data_2025.csv')
        weeks_2024_file: Path to 2024 season data (e.g., 'data/game_data_2024.csv')
        target_weeks_2024: List of 2024 weeks to include (e.g., [9,10,11,12,13,14,15,16,17])
        schedule_file: Path to the schedule CSV file (e.g., 'nfl2025sched.csv') (optional)
        current_week: Current week number for determining next opponent (optional)
        roster_file: Path to the active roster Excel file (default: 'data/master_roster.xlsx')
    """
    # Set global current week parameter for filename generation
    global current_week_param
    current_week_param = current_week if current_week is not None else 1
    
    start = dt.now()
    print(f"\nProjection Program Start with Time-Weighted Data - {start}:\n")
    print(f"Generating projections for Week {current_week_param}")
    print(f"Using time-weighted data with decay weighting\n")
    
    # Load active roster and player team mapping
    active_roster = load_active_roster(roster_file)
    player_team_mapping = create_player_team_mapping(roster_file)
    
    # Create time-weighted dataset with dynamic week selection
    df_season_data = create_time_weighted_dataset_dynamic(week_2025_file, weeks_2024_file, 
                                                         target_weeks_2024, current_week_param)
    
    # Load schedule data if provided
    df_schedule = None
    if schedule_file:
        print(f"Loading schedule data from {schedule_file}...")
        df_schedule = pd.read_csv(schedule_file)
        # Convert Round Number to numeric if it's not already
        df_schedule['Round Number'] = pd.to_numeric(df_schedule['Round Number'])
    
    # Create team and player datasets
    print("Creating team dataset...")
    df_team = create_team_dataset_from_game_data(df_season_data, df_schedule, current_week_param)
    
    print("Creating player dataset (active roster only, consolidated by current team)...")
    df_players = create_player_dataset_from_game_data(df_season_data, active_roster, player_team_mapping)
    
    # Save the created datasets for future use
    df_team.to_csv("nfl25_team.csv")
    df_players.to_csv("nfl25_players.csv")
    print("Saved team and player datasets")
    
    end = dt.now()
    print(f"\nProjection Program End - {end}\n Total: {end - start}\n")
    
    # Run analysis
    analyze(df_team, df_players, current_week_param)
## main
if __name__ == "__main__":
    import sys
    
    # Default parameters
    week_2025_file = "data/game_data_2025.csv"
    weeks_2024_file = "data/game_data_2024.csv"
    target_weeks_2024 = [9, 10, 11, 12, 13, 14, 15, 16, 17]
    schedule_file = "data/nfl-2025-EasternStandardTime.csv"
    current_week = 1  # Default to Week 1
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--week":
            # Specify current week: python projection.py --week 2
            if len(sys.argv) > 2:
                current_week = int(sys.argv[2])
            else:
                print("Usage: python projection.py --week <week_number>")
                print("Example: python projection.py --week 2")
                sys.exit(1)
        elif sys.argv[1] == "--time-weighted":
            # Legacy support: python projection.py --time-weighted schedule.csv week
            if len(sys.argv) > 2:
                schedule_file = sys.argv[2]
            if len(sys.argv) > 3:
                current_week = int(sys.argv[3])
        else:
            # Assume first argument is week number: python projection.py 2
            try:
                current_week = int(sys.argv[1])
            except ValueError:
                print(f"Invalid argument: {sys.argv[1]}")
                print("Usage: python projection.py [week_number]")
                print("Example: python projection.py 2")
                sys.exit(1)
    
    print(f"Running projections for Week {current_week}")
    run_with_time_weighted_data(week_2025_file, weeks_2024_file, target_weeks_2024, 
                              schedule_file, current_week)

