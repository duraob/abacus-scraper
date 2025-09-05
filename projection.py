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
    
    return team_opponents

def build_team_statistics(df_game_data):
    """
    Aggregate player-level data to team-level statistics for each game.
    
    This function creates both offensive and defensive team statistics:
    - Offensive stats: Direct aggregation of team's offensive performance
    - Defensive stats: Aggregation of opponent's offensive performance 
                      (represents how well the team's defense performed)
    
    Args:
        df_game_data: DataFrame with player performance data
    
    Returns:
        DataFrame with team-level aggregated stats per game
    """
    # Group by team, opponent, week and aggregate offensive stats
    # These represent the team's offensive performance in each game
    team_stats = df_game_data.groupby(['team', 'opponent', 'week']).agg({
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
    
    # Calculate defensive stats by aggregating opponent's offensive performance
    # When we group by opponent, we're getting the opponent's offensive stats
    # These become our defensive stats (how well we defended against them)
    opponent_offensive_stats = df_game_data.groupby(['opponent', 'team', 'week']).agg({
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
        df_schedule: Schedule DataFrame with columns [Week, away_team, home_team]
    
    Returns:
        Next opponent team name or None if on bye
    """
    # Find next game for this team (week > current_week)
    future_games = df_schedule[df_schedule['Week'] > current_week]
    
    # Find games where this team plays
    team_games = future_games[
        (future_games['away_team'] == team) | 
        (future_games['home_team'] == team)
    ]
    
    if team_games.empty:
        return None  # Team is on bye or no more games
    
    # Get the next game (lowest week number)
    next_game = team_games.loc[team_games['Week'].idxmin()]
    
    # Determine opponent
    if next_game['away_team'] == team:
        return next_game['home_team']
    else:
        return next_game['away_team']

def create_team_dataset_from_game_data(df_game_data, df_schedule=None, current_week=None):
    """
    Create a complete team dataset from player-level game data that's compatible
    with the existing analyze function.
    
    This function creates team-level statistics by:
    1. Aggregating each team's offensive performance across all games
    2. Aggregating each team's defensive performance (opponent offensive stats) across all games
    3. Adding schedule information for strength of schedule calculations
    
    Args:
        df_game_data: DataFrame with player performance data
        df_schedule: Schedule DataFrame with columns [Week, away_team, home_team] (optional)
        current_week: Current week number for determining next opponent (optional)
    
    Returns:
        DataFrame with team-level data including opps column and aggregated stats
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

def create_player_dataset_from_game_data(df_game_data, active_roster):
    """
    Create a player dataset from player-level game data that's compatible
    with the existing analyze function. Only includes players on the active roster.
    
    Args:
        df_game_data: DataFrame with player performance data
        active_roster: Set of active player names for filtering
    
    Returns:
        DataFrame with player-level aggregated stats for active players only
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
    
    # Group by player and team, aggregate stats across all games
    player_stats = df_filtered.groupby(['player', 'team']).agg({
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
    
    # Count games played (weeks) for each player
    games_played = df_filtered.groupby(['player', 'team'])['week'].nunique().reset_index()
    games_played.columns = ['player', 'team', 'g']
    
    # Merge stats with games played
    player_complete = pd.merge(player_stats, games_played, on=['player', 'team'], how='left')
    
    # Rename player column to 'name' to match expected format
    player_complete.rename(columns={'player': 'name'}, inplace=True)
    
    # Data validation: Remove any rows with invalid team names
    player_complete = player_complete[player_complete['team'].notna()]
    player_complete = player_complete[player_complete['team'] != '']
    player_complete = player_complete[player_complete['team'] != 0.0]
    
    print(f"Final player dataset size: {len(player_complete)} players")
    
    # Keep name as a regular column - let analyze function handle index management
    return player_complete

def analyze(df_team, df_players):
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
    
    # Generate filename based on current week
    current_week = getattr(globals(), 'current_week_param', 0)  # Default to 0 if not set
    filename = f"nfl25_proj_week{current_week}.csv"
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

def run_with_game_data(season_data_file, schedule_file=None, current_week=None, roster_file="data/master_roster.xlsx"):
    """
    Run the projection engine using game data from the new CSV format.
    Only includes players on the active roster to eliminate noise from inactive players.
    
    Args:
        season_data_file: Path to the game data CSV file (e.g., 'data/game_data_2024.csv')
        schedule_file: Path to the schedule CSV file (e.g., 'nfl2025sched.csv') (optional)
        current_week: Current week number for determining next opponent (optional)
        roster_file: Path to the active roster Excel file (default: 'data/master_roster.xlsx')
    """
    # Set global current week parameter for filename generation
    global current_week_param
    current_week_param = current_week if current_week is not None else 0
    
    start = dt.now()
    print(f"\nProjection Program Start with Game Data - {start}:\n")
    print(f"Generating projections for Week {current_week_param}\n")
    
    # Load active roster first
    active_roster = load_active_roster(roster_file)
    
    # Load game data
    print(f"Loading game data from {season_data_file}...")
    df_season_data = pd.read_csv(season_data_file)
    
    # Load schedule data if provided
    df_schedule = None
    if schedule_file:
        print(f"Loading schedule data from {schedule_file}...")
        df_schedule = pd.read_csv(schedule_file)
        # Convert Week to numeric if it's not already
        df_schedule['Week'] = pd.to_numeric(df_schedule['Week'])
    
    # Create team and player datasets
    print("Creating team dataset...")
    df_team = create_team_dataset_from_game_data(df_season_data, df_schedule, current_week)
    
    print("Creating player dataset (active roster only)...")
    df_players = create_player_dataset_from_game_data(df_season_data, active_roster)
    
    # Save the created datasets for future use
    df_team.to_csv("nfl25_team.csv")
    df_players.to_csv("nfl25_players.csv")
    print("Saved team and player datasets")
    
    end = dt.now()
    print(f"\nProjection Program End - {end}\n Total: {end - start}\n")
    
    # Run analysis
    analyze(df_team, df_players)
## main
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--game-data":
        if len(sys.argv) > 2:
            game_data_file = sys.argv[2]
        else:
            game_data_file = "data/game_data_2024.csv"  # Default to 2024 data
        
        # Optional schedule file and current week
        schedule_file = None
        current_week = None
        
        if len(sys.argv) > 3:
            schedule_file = sys.argv[3]
        if len(sys.argv) > 4:
            current_week = int(sys.argv[4])
        
        run_with_game_data(game_data_file, schedule_file, current_week)
    else:
        run()

