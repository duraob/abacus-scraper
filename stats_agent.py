"""
NFL Prop Nugget Module

This module analyzes NFL historical stats against current prop lines to generate
statistical insights and betting nuggets. It filters props to only include players
with historical game data and generates structured insights for LLM analysis.
"""

import os
import pandas as pd
import numpy as np
import json
import requests
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed. Install with: pip install python-dotenv")
    print("Continuing without environment variables...")


# Configuration constants
MIN_SAMPLE_SIZE = 3
MIN_DELTA_PERCENTAGE = 15.0
MAX_NUGGETS = 20

# GROK API Configuration
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"  # Adjust URL if needed
GROK_MODEL = "grok-4"  # Adjust model name if needed


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load and normalize all required data sources.
    
    Returns:
        tuple: (historical_stats, schedule, player_props)
    """
    print("Loading data sources...")
    
    # Load historical game data (all seasons)
    historical_stats = []
    data_dir = "data"
    
    for file in os.listdir(data_dir):
        if file.startswith("game_data_") and file.endswith(".csv"):
            file_path = os.path.join(data_dir, file)
            try:
                df = pd.read_csv(file_path)
                historical_stats.append(df)
                print(f"Loaded {file}: {len(df)} records")
            except Exception as e:
                print(f"Warning: Could not load {file}: {e}")
    
    if not historical_stats:
        raise FileNotFoundError("No historical game data files found")
    
    # Combine all historical data
    historical_stats = pd.concat(historical_stats, ignore_index=True)
    
    # Normalize column names
    historical_stats.columns = historical_stats.columns.str.lower().str.replace(' ', '_')
    
    # Load schedule
    schedule_file = os.path.join(data_dir, "nfl-2025-EasternStandardTime.csv")
    if not os.path.exists(schedule_file):
        raise FileNotFoundError(f"Schedule file not found: {schedule_file}")
    
    schedule = pd.read_csv(schedule_file)
    schedule.columns = schedule.columns.str.lower().str.replace(' ', '_')
    
    # Load player props (Week 1 for now)
    props_file = os.path.join(data_dir, "odds", "week_01", "player_props_week_01.csv")
    if not os.path.exists(props_file):
        raise FileNotFoundError(f"Player props file not found: {props_file}")
    
    player_props = pd.read_csv(props_file)
    player_props.columns = player_props.columns.str.lower().str.replace(' ', '_')
    
    print(f"Data loaded: {len(historical_stats)} historical records, {len(schedule)} games, {len(player_props)} props")
    
    return historical_stats, schedule, player_props


def create_player_mapping() -> Dict[str, str]:
    """
    Create mapping between odds player names and historical data player names.
    
    Returns:
        dict: Mapping of odds names to historical data names
    """
    mapping_file = 'data/player_name_mapping.csv'
    if os.path.exists(mapping_file):
        try:
            mapping_df = pd.read_csv(mapping_file)
            mapping = dict(zip(mapping_df['odds_name'], mapping_df['projection_name']))
            print(f"Loaded {len(mapping)} player mappings")
            return mapping
        except Exception as e:
            print(f"Warning: Could not load mapping file: {e}")
    
    # Fallback to basic mapping
    print("Using fallback player mapping")
    return {}


def filter_props_with_player_data(player_props: pd.DataFrame, 
                                historical_stats: pd.DataFrame,
                                player_mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Filter props to only include players with historical game data.
    
    Args:
        player_props: Player props dataframe
        historical_stats: Historical game stats dataframe
        player_mapping: Player name mapping dictionary
    
    Returns:
        DataFrame: Filtered props with only players having historical data
    """
    print("Filtering props to players with historical data...")
    
    # Get unique players from historical data
    historical_players = set(historical_stats['player'].unique())
    
    # Filter props to only include players with historical data
    filtered_props = []
    
    for _, prop in player_props.iterrows():
        player_name = prop['player_name']
        
        # Try direct match first
        if player_name in historical_players:
            filtered_props.append(prop)
            continue
        
        # Try mapped name
        if player_name in player_mapping:
            mapped_name = player_mapping[player_name]
            if mapped_name in historical_players:
                # Update the player name to match historical data
                prop_copy = prop.copy()
                prop_copy['player_name'] = mapped_name
                filtered_props.append(prop_copy)
                continue
    
    filtered_df = pd.DataFrame(filtered_props)
    print(f"Filtered from {len(player_props)} to {len(filtered_df)} props with historical data")
    
    return filtered_df


def get_stat_column(prop_type: str) -> Optional[str]:
    """
    Map prop type to corresponding historical stat column.
    
    Args:
        prop_type: Type of prop (rush_yds, reception_yds, etc.)
    
    Returns:
        str: Corresponding historical stat column name
    """
    prop_mapping = {
        'rush_yds': 'rush_yds',
        'reception_yds': 'rec_yds',
        'receptions': 'receptions',
        'pass_yds': 'pass_yds',
        'pass_attempts': 'pass_att',
        'pass_completions': 'pass_cmp',
        'pass_tds': 'pass_tds',
        'pass_interceptions': 'pass_int',
        'rush_att': 'rush_att',
        'anytime_td': 'rush_tds'  # Will combine with rec_tds
    }
    
    return prop_mapping.get(prop_type)


def compute_trends(filtered_props: pd.DataFrame, 
                  historical_stats: pd.DataFrame) -> List[Dict]:
    """
    Compute player trends for each prop.
    
    Args:
        filtered_props: Filtered player props
        historical_stats: Historical game stats
    
    Returns:
        list: List of trend dictionaries
    """
    print("Computing player trends...")
    
    trends = []
    
    for _, prop in filtered_props.iterrows():
        player_name = prop['player_name']
        prop_type = prop['prop_type']
        line = prop['point']
        
        # Get stat column for this prop type
        stat_col = get_stat_column(prop_type)
        if not stat_col:
            continue
        
        # Get player's historical data
        player_data = historical_stats[historical_stats['player'] == player_name]
        if player_data.empty:
            continue
        
        # Get opponent from schedule (simplified - would need proper game matching)
        # For now, we'll use a placeholder approach
        opponent = "Unknown"  # This would need proper game matching logic
        
        # Calculate career average for this stat
        if prop_type == 'anytime_td':
            # Combine rushing and receiving TDs
            total_tds = player_data['rush_tds'].fillna(0) + player_data['rec_tds'].fillna(0)
            career_avg = total_tds.mean()
        else:
            career_avg = player_data[stat_col].fillna(0).mean()
        
        # Calculate last 3 games vs opponent (if available)
        # This would need proper opponent matching logic
        last_3_vs_opponent = career_avg  # Placeholder
        
        # Calculate last 5 overall games (form check)
        last_5_games = player_data.tail(5)[stat_col].fillna(0).mean()
        
        # Calculate sample size
        sample_size = len(player_data)
        
        if sample_size >= MIN_SAMPLE_SIZE:
            trend_data = {
                'player': player_name,
                'opponent': opponent,
                'stat': prop_type,
                'sample_size': sample_size,
                'career_avg': career_avg,
                'last_3_vs_opponent': last_3_vs_opponent,
                'last_5_games': last_5_games,
                'line': line,
                'stat_column': stat_col
            }
            trends.append(trend_data)
    
    print(f"Computed trends for {len(trends)} player/prop combinations")
    return trends


def generate_nuggets(trends: List[Dict]) -> List[Dict]:
    """
    Generate raw nugget dictionaries from trends.
    
    Args:
        trends: List of trend dictionaries
    
    Returns:
        list: List of nugget dictionaries
    """
    print("Generating nuggets...")
    
    nuggets = []
    seen_combinations = set()  # Track unique player/stat combinations
    
    for trend in trends:
        # Create unique key for this player/stat combination
        unique_key = (trend['player'], trend['stat'])
        
        # Skip if we've already seen this combination
        if unique_key in seen_combinations:
            continue
        
        seen_combinations.add(unique_key)
        
        # Use career average for now (could be enhanced with opponent-specific data)
        average = trend['career_avg']
        line = trend['line']
        
        # Calculate delta and percentage
        delta = average - line
        delta_pct = (delta / line) * 100 if line != 0 else 0
        
        # Apply filters
        if abs(delta_pct) >= MIN_DELTA_PERCENTAGE:
            nugget = {
                'player': trend['player'],
                'opponent': trend['opponent'],
                'stat': trend['stat'],
                'sample_size': trend['sample_size'],
                'average': round(average, 1),
                'line': line,
                'delta_pct': round(delta_pct, 1),
                'nugget': f"{trend['player']} averages {average:.1f} {trend['stat']} in {trend['sample_size']} games, {delta_pct:+.1f}% vs Week 1 line of {line}."
            }
            nuggets.append(nugget)
    
    print(f"Generated {len(nuggets)} unique nuggets meeting criteria")
    return nuggets


def filter_and_rank_nuggets(nuggets: List[Dict]) -> List[Dict]:
    """
    Apply final filters and rank nuggets by delta percentage.
    
    Args:
        nuggets: List of raw nuggets
    
    Returns:
        list: Filtered and ranked nuggets
    """
    print("Filtering and ranking nuggets...")
    
    # Filter by sample size and delta percentage
    filtered_nuggets = [
        nugget for nugget in nuggets 
        if nugget['sample_size'] >= MIN_SAMPLE_SIZE 
        and abs(nugget['delta_pct']) >= MIN_DELTA_PERCENTAGE
    ]
    
    # Rank by absolute delta percentage (descending)
    ranked_nuggets = sorted(
        filtered_nuggets, 
        key=lambda x: abs(x['delta_pct']), 
        reverse=True
    )
    
    # Keep top nuggets
    final_nuggets = ranked_nuggets[:MAX_NUGGETS]
    
    print(f"Final result: {len(final_nuggets)} nuggets")
    return final_nuggets


def save_nuggets_to_json(nuggets: List[Dict], week_number: int = 1) -> str:
    """
    Save nuggets to JSON file.
    
    Args:
        nuggets: List of nugget dictionaries
        week_number: NFL week number
    
    Returns:
        str: Path to saved JSON file
    """
    # Create nuggets directory
    nuggets_dir = "data/nuggets"
    os.makedirs(nuggets_dir, exist_ok=True)
    
    filename = f"nuggets_week_{week_number:02d}.json"
    filepath = os.path.join(nuggets_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(nuggets, f, indent=2)
    
    print(f"Saved {len(nuggets)} nuggets to {filepath}")
    return filepath


def send_to_llm(json_file: str, prompt: str) -> str:
    """
    Send JSON data to LLM with prompt for analysis.
    
    Args:
        json_file: Path to JSON file with nuggets
        prompt: Prompt for LLM analysis
    
    Returns:
        str: LLM response (placeholder for now)
    """
    print("Preparing data for LLM analysis...")
    
    # Read the JSON file
    with open(json_file, 'r') as f:
        nuggets_data = json.load(f)
    
    # Create the fixed prompt as specified in the execution document
    llm_prompt = f"""You are an ESPN sports analytics writer. 
You are given structured NFL trend nuggets in JSON. 
Rewrite each nugget as a short, headline-style betting insight. 
- Keep it one sentence each. 
- Make it punchy and fan-friendly. 
- Always connect to the posted prop line. 
- Example: "Derrick Henry has punished the Ravens, averaging 122 rushing yards in 5 career games — well above his Week 1 line of 89.5."

Here are the nuggets to analyze:
{json.dumps(nuggets_data, indent=2)}

Return your analysis as a list of ESPN-style insights."""

    # For now, just return the prompt (in real implementation, this would call an LLM API)
    print("LLM prompt prepared:")
    print(llm_prompt)
    
    return llm_prompt


def call_grok_api(nuggets_data: List[Dict]) -> Dict:
    """
    Call GROK API to analyze nuggets and generate ESPN-style insights.
    
    Args:
        nuggets_data: List of nugget dictionaries
    
    Returns:
        dict: GROK API response with ESPN-style insights
    """
    if not GROK_API_KEY:
        print("❌ GROK_API_KEY not found in environment variables")
        print("Please add GROK_API_KEY to your .env file")
        return {"error": "GROK_API_KEY not configured"}
    
    print("🤖 Calling GROK API for ESPN-style analysis...")
    
    # Prepare the prompt for GROK
    grok_prompt = f"""You are an ESPN sports analytics writer. 
You are given structured NFL trend nuggets in JSON. 
Rewrite each nugget as a short, headline-style betting insight. 
- Keep it one sentence each. 
- Make it punchy and fan-friendly. 
- Always connect to the posted prop line. 
- Example: "Derrick Henry has punished the Ravens, averaging 122 rushing yards in 5 career games — well above his Week 1 line of 89.5."

Here are the nuggets to analyze:
{json.dumps(nuggets_data, indent=2)}

Return your analysis as a JSON list of ESPN-style insights."""

    # Prepare the API request
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": GROK_MODEL,
        "messages": [
            {
                "role": "user",
                "content": grok_prompt
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.7
    }
    
    try:
        print(f"📡 Sending request to GROK API...")
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ GROK API call successful")
            
            # Extract the response content
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print("📝 GROK Response:")
                print(content)
                
                # Try to parse JSON response
                try:
                    parsed_response = json.loads(content)
                    return {
                        "success": True,
                        "insights": parsed_response,
                        "raw_response": content
                    }
                except json.JSONDecodeError:
                    # If not JSON, return as text
                    return {
                        "success": True,
                        "insights": [content],
                        "raw_response": content
                    }
            else:
                return {
                    "success": False,
                    "error": "No response content from GROK API",
                    "raw_response": result
                }
        else:
            print(f"❌ GROK API error: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "error": f"API error {response.status_code}",
                "raw_response": response.text
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return {
            "success": False,
            "error": f"Request error: {str(e)}"
        }
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def save_grok_insights(insights: Dict, week_number: int = 1) -> str:
    """
    Save GROK-generated insights to a file.
    
    Args:
        insights: GROK API response dictionary
        week_number: NFL week number
    
    Returns:
        str: Path to saved insights file
    """
    # Create insights directory
    insights_dir = "data/insights"
    os.makedirs(insights_dir, exist_ok=True)
    
    filename = f"grok_insights_week_{week_number:02d}.json"
    filepath = os.path.join(insights_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(insights, f, indent=2)
    
    print(f"💾 Saved GROK insights to {filepath}")
    return filepath


def main(week_number: int = 1) -> Tuple[List[Dict], str]:
    """
    Main execution function for the NFL Prop Nugget Module.
    
    Args:
        week_number: NFL week number to analyze
    
    Returns:
        tuple: (nuggets, llm_prompt)
    """
    print(f"=== NFL Prop Nugget Module - Week {week_number} ===")
    
    try:
        # 1. Load and normalize data
        historical_stats, schedule, player_props = load_data()
        
        # 2. Create player mapping
        player_mapping = create_player_mapping()
        
        # 3. Filter props to players with historical data
        filtered_props = filter_props_with_player_data(
            player_props, historical_stats, player_mapping
        )
        
        # 4. Compute player trends
        trends = compute_trends(filtered_props, historical_stats)
        
        # 5. Generate nuggets
        raw_nuggets = generate_nuggets(trends)
        
        # 6. Filter and rank nuggets
        final_nuggets = filter_and_rank_nuggets(raw_nuggets)
        
        # 7. Save nuggets to JSON
        json_file = save_nuggets_to_json(final_nuggets, week_number)
        
        # 8. Prepare for LLM analysis
        llm_prompt = send_to_llm(json_file, "")
        
        # 9. Call GROK API for ESPN-style insights
        grok_response = call_grok_api(final_nuggets)
        
        # 10. Save GROK insights
        if grok_response.get("success"):
            insights_file = save_grok_insights(grok_response, week_number)
            print(f"🤖 GROK insights saved to: {insights_file}")
        else:
            print(f"⚠️ GROK API call failed: {grok_response.get('error', 'Unknown error')}")
        
        print(f"\n✅ Successfully processed Week {week_number}")
        print(f"📊 Generated {len(final_nuggets)} nuggets")
        print(f"💾 Saved to: {json_file}")
        print(f"🤖 LLM prompt prepared for analysis")
        print(f"🤖 GROK API integration: {'✅ Success' if grok_response.get('success') else '❌ Failed'}")
        
        return final_nuggets, llm_prompt
        
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
        raise


if __name__ == "__main__":
    # Run for Week 1 by default
    main(1)
