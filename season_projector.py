"""
Season-Long NFL Projection System

Generates season-long projections by running the existing weekly projection engine
for all 18 weeks of the NFL season and accumulating the results.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime as dt
from projection import run_with_time_weighted_data, analyze

def run_season_projections(week_2025_file="data/game_data_2025.csv", 
                          weeks_2024_file="data/game_data_2024.csv",
                          target_weeks_2024=[9, 10, 11, 12, 13, 14, 15, 16, 17],
                          schedule_file="data/nfl-2025-EasternStandardTime.csv",
                          roster_file="data/master_roster.xlsx"):
    """
    Run season-long projections by generating weekly projections for all 18 weeks
    and accumulating the results into season totals.
    
    Args:
        week_2025_file: Path to 2025 season data
        weeks_2024_file: Path to 2024 season data
        target_weeks_2024: List of 2024 weeks to include as fallback
        schedule_file: Path to the schedule CSV file
        roster_file: Path to the active roster Excel file
    """
    start = dt.now()
    print(f"\nSeason-Long Projection System Start - {start}:\n")
    
    # Create season projections directory
    season_dir = "data/season_projections"
    os.makedirs(season_dir, exist_ok=True)
    
    # Initialize season accumulation dataframes
    season_player_stats = None
    season_team_stats = None
    
    # Run projections for each week (1-18 for full season)
    for week in range(1, 19):  # Full season: weeks 1-18
        print(f"\n{'='*50}")
        print(f"Processing Week {week}")
        print(f"{'='*50}")
        
        try:
            # Run weekly projections using existing system
            # Import the analyze function directly to avoid file conflicts
            from projection import (load_active_roster, create_player_team_mapping, 
                                  create_time_weighted_dataset_dynamic, 
                                  create_team_dataset_from_game_data, 
                                  create_player_dataset_from_game_data, analyze)
            
            # Load active roster and player team mapping
            active_roster = load_active_roster(roster_file)
            player_team_mapping = create_player_team_mapping(roster_file)
            
            # Create time-weighted dataset with dynamic week selection
            df_season_data = create_time_weighted_dataset_dynamic(week_2025_file, weeks_2024_file, 
                                                               target_weeks_2024, week)
            
            # Load schedule data if provided
            df_schedule = None
            if schedule_file:
                df_schedule = pd.read_csv(schedule_file)
                df_schedule['Round Number'] = pd.to_numeric(df_schedule['Round Number'])
            
            # Create team and player datasets
            df_team = create_team_dataset_from_game_data(df_season_data, df_schedule, week)
            df_players = create_player_dataset_from_game_data(df_season_data, active_roster, player_team_mapping)
            
            # Run analysis using the regular analyze function
            analyze(df_team, df_players, week)
            
            # Copy the generated weekly projections to season directory
            source_file = f"data/projections/nfl25_proj_week{week}.csv"
            dest_file = os.path.join(season_dir, f"nfl25_proj_week{week}.csv")
            
            if os.path.exists(source_file):
                # Copy file to season directory
                import shutil
                shutil.copy2(source_file, dest_file)
                
                # Load the weekly projections
                df_weekly = pd.read_csv(dest_file)
                
                # Add week column
                df_weekly['week'] = week
                
                # Accumulate season stats
                if season_player_stats is None:
                    season_player_stats = df_weekly.copy()
                else:
                    season_player_stats = pd.concat([season_player_stats, df_weekly], ignore_index=True)
                
                print(f"Week {week}: {len(df_weekly)} players projected")
            else:
                print(f"Warning: Weekly projections file not found for Week {week}")
                
        except Exception as e:
            print(f"Error processing Week {week}: {e}")
            continue
    
    # Generate season-long summaries
    if season_player_stats is not None:
        generate_season_summaries(season_player_stats, season_dir)
    
    end = dt.now()
    print(f"\nSeason-Long Projection System End - {end}")
    print(f"Total Runtime: {end - start}\n")

def generate_season_summaries(season_data, output_dir):
    """
    Generate season-long summary statistics and projections.
    
    Args:
        season_data: DataFrame with all weekly projections
        output_dir: Directory to save season summaries
    """
    print("\nGenerating season-long summaries...")
    
    # Player season totals
    player_season_totals = season_data.groupby('name').agg({
        'proj_pass_att': 'sum',
        'proj_rush_att': 'sum', 
        'proj_tar': 'sum',
        'proj_pass_yd': 'sum',
        'proj_rush_yd': 'sum',
        'proj_rec_yd': 'sum',
        'proj_pass_td': 'sum',
        'proj_rush_td': 'sum',
        'proj_rec_td': 'sum',
        'proj_int': 'sum',
        'proj_fum': 'sum',
        'team': 'first',
        'week': 'count'  # Games played
    }).rename(columns={'week': 'games_played'})
    
    # Calculate fantasy points (standard scoring)
    player_season_totals['fantasy_points'] = (
        player_season_totals['proj_pass_yd'] * 0.04 +
        player_season_totals['proj_rush_yd'] * 0.1 +
        player_season_totals['proj_rec_yd'] * 0.1 +
        player_season_totals['proj_pass_td'] * 4 +
        player_season_totals['proj_rush_td'] * 6 +
        player_season_totals['proj_rec_td'] * 6 +
        player_season_totals['proj_int'] * -2 +
        player_season_totals['proj_fum'] * -2
    )
    
    # Team season totals
    team_season_totals = season_data.groupby('team').agg({
        'proj_pass_att': 'sum',
        'proj_rush_att': 'sum',
        'proj_tar': 'sum', 
        'proj_pass_yd': 'sum',
        'proj_rush_yd': 'sum',
        'proj_rec_yd': 'sum',
        'proj_pass_td': 'sum',
        'proj_rush_td': 'sum',
        'proj_rec_td': 'sum',
        'proj_int': 'sum',
        'proj_fum': 'sum',
        'week': 'count'
    }).rename(columns={'week': 'total_games'})
    
    # Save season summaries
    player_season_totals.to_csv(os.path.join(output_dir, "player_season_totals.csv"))
    team_season_totals.to_csv(os.path.join(output_dir, "team_season_totals.csv"))
    
    # Generate top performers
    top_qbs = player_season_totals[player_season_totals['proj_pass_att'] > 0].nlargest(10, 'fantasy_points')
    top_rbs = player_season_totals[player_season_totals['proj_rush_att'] > 0].nlargest(10, 'fantasy_points')
    top_wrs = player_season_totals[player_season_totals['proj_tar'] > 0].nlargest(10, 'fantasy_points')
    
    # Save top performers
    top_qbs.to_csv(os.path.join(output_dir, "top_qbs_season.csv"))
    top_rbs.to_csv(os.path.join(output_dir, "top_rbs_season.csv"))
    top_wrs.to_csv(os.path.join(output_dir, "top_wrs_season.csv"))
    
    print(f"Season summaries saved to {output_dir}/")
    print(f"Total players projected: {len(player_season_totals)}")
    print(f"Total teams: {len(team_season_totals)}")
    
    # Print top performers
    print("\nTop 5 QBs by Fantasy Points:")
    print(top_qbs[['team', 'fantasy_points', 'proj_pass_yd', 'proj_pass_td']].head())
    
    print("\nTop 5 RBs by Fantasy Points:")
    print(top_rbs[['team', 'fantasy_points', 'proj_rush_yd', 'proj_rush_td']].head())
    
    print("\nTop 5 WRs by Fantasy Points:")
    print(top_wrs[['team', 'fantasy_points', 'proj_rec_yd', 'proj_rec_td']].head())

if __name__ == "__main__":
    run_season_projections()
