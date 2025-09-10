"""
Odds Scraper - The Odds API Integration
Production module for collecting NFL odds data efficiently
"""

import requests
import json
import os
import time
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('odds_scraper.log'),
        logging.StreamHandler()
    ]
)

class OddsScraper:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ODDS_API_KEY')
        self.base_url = "https://api.the-odds-api.com/v4"
        self.cache_dir = 'cache/odds'
        self.data_dir = 'data/odds'
        
        # Free tier rate limiting: 3 requests per minute = 20 seconds between requests
        self.min_request_interval = 20  # seconds
        self.last_request_time = 0
        self.request_count = 0
        self.monthly_limit = 500
        
        # Create directories
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Log API key status (without exposing the actual key)
        if self.api_key:
            logging.info(f"API key loaded successfully. Key length: {len(self.api_key)} characters")
            logging.info(f"API key starts with: {self.api_key[:8]}...")
            logging.info(f"Rate limiting: {self.min_request_interval}s between requests (free tier)")
        else:
            logging.error("No API key found. Please check your .env file contains ODDS_API_KEY")
        
        if not self.api_key:
            raise ValueError("API key required. Set ODDS_API_KEY environment variable.")
    
    def _enforce_rate_limit(self):
        """
        Enforce free tier rate limiting: 3 requests per minute.
        Ensures at least 20 seconds between API calls.
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            logging.info(f"Rate limiting: waiting {wait_time:.1f}s before next request")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # Log monthly usage
        if self.request_count % 10 == 0:  # Log every 10 requests
            logging.info(f"Monthly request count: {self.request_count}/{self.monthly_limit}")
        
        # Warn when approaching limit
        if self.request_count >= self.monthly_limit * 0.9:
            logging.warning(f"⚠️  Approaching monthly limit: {self.request_count}/{self.monthly_limit}")
        elif self.request_count >= self.monthly_limit:
            logging.error(f"🚫 Monthly limit reached: {self.request_count}/{self.monthly_limit}")
            raise ValueError("Monthly API request limit reached. Please upgrade or wait until next month.")
    
    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Tuple[Optional[Dict], Dict]:
        """Make API request with error handling and rate limiting"""
        # Enforce free tier rate limiting
        self._enforce_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apiKey'] = self.api_key
        
        try:
            logging.info(f"Making request to: {endpoint}")
            response = requests.get(url, params=params)
            
            # Log rate limit info
            remaining = response.headers.get('x-requests-remaining', 'unknown')
            used = response.headers.get('x-requests-used', 'unknown')
            logging.info(f"API Usage - Remaining: {remaining}, Used: {used}")
            
            if response.status_code == 200:
                return response.json(), response.headers
            elif response.status_code == 429:
                logging.error("Rate limit exceeded. Waiting 60 seconds...")
                time.sleep(60)
                return self.make_request(endpoint, params)
            else:
                logging.error(f"API request failed: {response.status_code} - {response.text}")
                return None, response.headers
                
        except Exception as e:
            logging.error(f"Request error: {e}")
            return None, {}
    
    def _get_week_dates_from_csv(self, week: int, year: int) -> Dict[str, str]:
        """
        Get start and end dates for a specific week from NFL schedule CSV.
        
        Args:
            week (int): NFL week number
            year (int): NFL season year
            
        Returns:
            Dict[str, str]: Dictionary with 'start' and 'end' ISO date strings
        """
        try:
            # Read the NFL schedule CSV
            schedule_path = 'data/nfl-2025-EasternStandardTime.csv'
            
            if not os.path.exists(schedule_path):
                logging.error(f"NFL schedule CSV not found at: {schedule_path}")
                return {'start': None, 'end': None}
            
            # Parse the CSV to get dates for the specified week
            schedule_df = pd.read_csv(schedule_path)
            
            # Filter for the specific week
            week_matchups = schedule_df[schedule_df['Round Number'] == week].copy()
            
            if week_matchups.empty:
                logging.warning(f"No matchups found in schedule for Week {week}, {year}")
                return {'start': None, 'end': None}
            
            # Get start (earliest) and end (latest) dates for the week
            week_dates = pd.to_datetime(week_matchups['Date'])
            start_date = week_dates.min()
            end_date = week_dates.max() + timedelta(days=1)  # Include full day
            
            # Convert to ISO 8601 format for API (UTC timezone)
            start_iso = start_date.strftime('%Y-%m-%dT00:00:00Z')
            end_iso = end_date.strftime('%Y-%m-%dT23:59:59Z')
            
            logging.info(f"Week {week} date range: {start_date.date()} to {end_date.date()}")
            return {'start': start_iso, 'end': end_iso}
            
        except Exception as e:
            logging.error(f"Error getting week dates from CSV: {e}")
            return {'start': None, 'end': None}
    
    def get_nfl_events(self, week: int = None, year: int = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict]:
        """Get NFL events with team odds (h2h, spreads, totals)"""
        logging.info("Fetching NFL events with team odds...")
        
        # If week and year provided, get dates from CSV
        if week and year:
            week_dates = self._get_week_dates_from_csv(week, year)
            if week_dates['start'] and week_dates['end']:
                date_from = week_dates['start']
                date_to = week_dates['end']
                logging.info(f"Filtering events for Week {week}: {date_from} to {date_to}")
        
        params = {
            'commenceTimeFrom': date_from,
            'commenceTimeTo': date_to,
            'sport' : 'americanfootball_nfl',
            'regions': 'us',
            'markets': 'h2h,spreads,totals',
            'oddsFormat': 'american',
            'bookmakers': 'draftkings'  # Focus on DraftKings for consistency
        }
        
        # Add date filters if provided
        if date_from:
            params['commenceTimeFrom'] = date_from
        if date_to:
            params['commenceTimeTo'] = date_to
        
        data, headers = self.make_request("/sports/americanfootball_nfl/odds", params)
        
        if data:
            # Save raw response
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nfl_team_odds_{timestamp}.json"
            with open(os.path.join(self.cache_dir, filename), 'w') as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"Retrieved {len(data)} NFL events")
            return data
        
        return []
    
    def get_player_props(self, event_id: str) -> Optional[Dict]:
        """Get player props for a specific event"""
        logging.info(f"Fetching player props for event: {event_id}")
        
        # Available player prop markets for NFL
        player_markets = [
            "player_pass_attempts",
            "player_pass_completions",
            "player_pass_interceptions",
            "player_pass_rush_reception_tds",
            "player_pass_rush_reception_yds",
            "player_pass_tds",
            "player_pass_yds",
            "player_receptions",
            "player_reception_tds",
            "player_reception_yds",
            "player_rush_tds",
            "player_rush_yds",
            "player_anytime_td"
        ]
        
        sport = 'americanfootball_nfl'

        params = {
            'sport' : sport,
            'event_id' : event_id,
            'regions': 'us',
            'markets': ','.join(player_markets),
            'oddsFormat': 'american',
            'bookmakers': 'draftkings',
        }
        
        data, headers = self.make_request(f"/sports/{sport}/events/{event_id}/odds", params)
        
        if data:
            # Save raw response
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"player_props_{event_id}_{timestamp}.json"
            with open(os.path.join(self.cache_dir, filename), 'w') as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"Retrieved player props for event {event_id}")
            return data
        
        return None
    
    def transform_team_odds(self, events_data: List[Dict]) -> pd.DataFrame:
        """Transform team odds data into structured DataFrame"""
        logging.info("Transforming team odds data...")
        
        team_odds = []
        
        for event in events_data:
            event_id = event['id']
            sport_key = event['sport_key']
            commence_time = event['commence_time']
            home_team = event['home_team']
            away_team = event['away_team']
            
            # Process each bookmaker
            for bookmaker in event.get('bookmakers', []):
                bookmaker_key = bookmaker['key']
                bookmaker_title = bookmaker['title']
                
                # Process each market
                for market in bookmaker.get('markets', []):
                    market_key = market['key']
                    
                    # Process each outcome
                    for outcome in market.get('outcomes', []):
                        odds_record = {
                            'event_id': event_id,
                            'sport_key': sport_key,
                            'commence_time': commence_time,
                            'home_team': home_team,
                            'away_team': away_team,
                            'bookmaker_key': bookmaker_key,
                            'bookmaker_title': bookmaker_title,
                            'market_key': market_key,
                            'outcome_name': outcome['name'],
                            'price': outcome['price'],
                            'point': outcome.get('point'),  # For spreads/totals
                            'description': outcome.get('description')  # For player props
                        }
                        team_odds.append(odds_record)
        
        df = pd.DataFrame(team_odds)
        return df
    
    def transform_player_props(self, props_data: Dict) -> pd.DataFrame:
        """Transform player props data into structured DataFrame"""
        logging.info("Transforming player props data...")
        
        player_props = []
        
        event_id = props_data['id']
        sport_key = props_data['sport_key']
        commence_time = props_data['commence_time']
        home_team = props_data['home_team']
        away_team = props_data['away_team']
        
        # Process each bookmaker
        for bookmaker in props_data.get('bookmakers', []):
            bookmaker_key = bookmaker['key']
            bookmaker_title = bookmaker['title']
            
            # Process each market
            for market in bookmaker.get('markets', []):
                market_key = market['key']
                
                # Process each outcome
                for outcome in market.get('outcomes', []):
                    prop_record = {
                        'event_id': event_id,
                        'sport_key': sport_key,
                        'commence_time': commence_time,
                        'home_team': home_team,
                        'away_team': away_team,
                        'bookmaker_key': bookmaker_key,
                        'bookmaker_title': bookmaker_title,
                        'market_key': market_key,
                        'outcome_name': outcome['name'],
                        'price': outcome['price'],
                        'point': outcome.get('point'),
                        'player_name': outcome.get('description'),  # Player name for props
                        'prop_type': market_key.replace('player_', '')  # Clean prop type
                    }
                    player_props.append(prop_record)
        
        df = pd.DataFrame(player_props)
        return df
    
    def scrape_week_odds(self, week: int = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Main method to scrape odds for a specific week (team + player props).
        Organizes output into weekly folders based on NFL schedule.
        
        Args:
            week (int, optional): Specific week to scrape. If None, uses current week.
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: Team odds and player props DataFrames
        """
        if week is None:
            # Determine current NFL week
            target_week = self.get_current_nfl_week()
            logging.info(f"Auto-detected current NFL week: {target_week}")
        else:
            target_week = week
            logging.info(f"Scraping odds for specified week: {target_week}")
        
        # Get week dates from NFL schedule
        week_dates = self._get_week_dates_from_csv(target_week, 2025)
        if not week_dates['start'] or not week_dates['end']:
            logging.warning("Could not determine week dates, using fallback")
            # Fallback to Thursday-Monday calculation
            today = datetime.now()
            thursday = today - timedelta(days=today.weekday() - 3)
            monday = thursday + timedelta(days=4)
            date_from = thursday.strftime("%Y-%m-%dT00:00:00Z")
            date_to = monday.strftime("%Y-%m-%dT23:59:59Z")
        else:
            date_from = week_dates['start']
            date_to = week_dates['end']
        
        logging.info(f"Scraping odds from {date_from} to {date_to}")
        
        # Step 1: Get team odds
        team_events = self.get_nfl_events(date_from=date_from, date_to=date_to)
        
        if not team_events:
            logging.warning("No team events found")
            return pd.DataFrame(), pd.DataFrame()
        
        # Transform team odds
        team_odds_df = self.transform_team_odds(team_events)
        
        # Step 2: Get player props for each event
        all_player_props = []
        
        for event in team_events:
            event_id = event['id']
            logging.info(f"Getting player props for event: {event_id}")
            
            props_data = self.get_player_props(event_id)
            if props_data:
                props_df = self.transform_player_props(props_data)
                all_player_props.append(props_df)
            
            # Rate limiting is now handled automatically in make_request()
        
        # Combine all player props
        player_props_df = pd.concat(all_player_props, ignore_index=True) if all_player_props else pd.DataFrame()
        
        # Save to weekly directory with organized file names
        week_dir = self.get_weekly_directory(target_week)
        
        if not team_odds_df.empty:
            team_file = os.path.join(week_dir, f'team_odds_week_{target_week:02d}.csv')
            team_odds_df.to_csv(team_file, index=False)
            logging.info(f"Saved {len(team_odds_df)} team odds records to {team_file}")
        
        if not player_props_df.empty:
            props_file = os.path.join(week_dir, f'player_props_week_{target_week:02d}.csv')
            player_props_df.to_csv(props_file, index=False)
            logging.info(f"Saved {len(player_props_df)} player prop records to {props_file}")
        
        return team_odds_df, player_props_df

    def scrape_current_week_odds(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Legacy method for backward compatibility.
        Scrapes current week odds automatically.
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: Team odds and player props DataFrames
        """
        return self.scrape_week_odds(week=None)
    
    def test_api_connection(self) -> bool:
        """
        Test the API connection to verify the API key is working.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logging.info("Testing API connection...")
            data, headers = self.make_request("/sports")
            
            if data is not None:
                logging.info("API connection SUCCESSFUL!")
                return True
            else:
                logging.error("API connection FAILED")
                return False
                
        except Exception as e:
            logging.error(f"API connection test FAILED: {e}")
            return False
    
    def get_usage_info(self) -> Dict:
        """Get current API usage information"""
        # Make a simple request to get usage headers
        data, headers = self.make_request("/sports")
        
        return {
            'remaining': headers.get('x-requests-remaining', 'unknown'),
            'used': headers.get('x-requests-used', 'unknown'),
            'last_cost': headers.get('x-requests-last', 'unknown'),
            'monthly_count': self.request_count,
            'monthly_limit': self.monthly_limit,
            'rate_limit_interval': f"{self.min_request_interval}s"
        }
    
    def get_monthly_usage(self) -> Dict:
        """
        Get monthly usage statistics for the free tier.
        
        Returns:
            Dict: Monthly usage information
        """
        return {
            'requests_used': self.request_count,
            'requests_remaining': self.monthly_limit - self.request_count,
            'monthly_limit': self.monthly_limit,
            'usage_percentage': (self.request_count / self.monthly_limit) * 100
        }

    def get_current_nfl_week(self) -> int:
        """
        Determine current NFL week based on schedule and current date.
        
        Returns:
            int: Current NFL week number (1-18 for regular season)
        """
        try:
            schedule_df = pd.read_csv('data/nfl-2025-EasternStandardTime.csv')
            schedule_df['Date'] = pd.to_datetime(schedule_df['Date'])
            
            today = datetime.now().date()
            
            # Find the next week that hasn't started yet
            for week in sorted(schedule_df['Round Number'].unique()):
                week_dates = schedule_df[schedule_df['Round Number'] == week]['Date'].dt.date
                if min(week_dates) > today:
                    return week - 1  # Return the current week
            
            # If we're past all weeks, return the last week
            return schedule_df['Round Number'].max()
            
        except Exception as e:
            logging.error(f"Error determining NFL week: {e}")
            return 1  # Fallback to week 1
    
    def get_weekly_directory(self, week: int) -> str:
        """
        Create and return path to weekly odds directory.
        
        Args:
            week (int): NFL week number
            
        Returns:
            str: Path to the weekly directory
        """
        week_dir = os.path.join(self.data_dir, f'week_{week:02d}')
        os.makedirs(week_dir, exist_ok=True)
        return week_dir

def main(week: int = None):
    """
    Main execution function
    
    Args:
        week (int, optional): Specific week to scrape. If None, auto-detects current week.
    """
    print("=== NFL Odds Scraper ===")
    
    if week:
        print(f"Scraping odds for Week {week}")
    else:
        print("Auto-detecting current week")
    
    try:
        scraper = OddsScraper()
        
        # Test API connection first
        if not scraper.test_api_connection():
            print("API connection FAILED. Please check your API key and internet connection.")
            return
        
        print("API connection SUCCESSFUL!")
        
        # Check usage
        usage = scraper.get_usage_info()
        print(f"API Usage - Remaining: {usage['remaining']}, Used: {usage['used']}")
        
        # Check monthly usage
        monthly_usage = scraper.get_monthly_usage()
        print(f"Monthly Usage: {monthly_usage['requests_used']}/{monthly_usage['monthly_limit']} ({monthly_usage['usage_percentage']:.1f}%)")
        
        # Scrape odds for specified week or current week
        team_odds, player_props = scraper.scrape_week_odds(week=week)
        
        print(f"\nResults:")
        print(f"Team Odds: {len(team_odds)} records")
        print(f"Player Props: {len(player_props)} records")
        
        # Final usage report
        final_usage = scraper.get_monthly_usage()
        print(f"\nFinal Monthly Usage: {final_usage['requests_used']}/{final_usage['monthly_limit']} ({final_usage['usage_percentage']:.1f}%)")
        
        if not team_odds.empty:
            print(f"\nSample Team Odds:")
            print(team_odds.head())
        
        if not player_props.empty:
            print(f"\nSample Player Props:")
            print(player_props.head())
        
    except Exception as e:
        logging.error(f"Scraper failed: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    week = None
    if len(sys.argv) > 1:
        try:
            week = int(sys.argv[1])
            print(f"Scraping odds for Week {week}")
        except ValueError:
            print(f"Invalid week number: {sys.argv[1]}")
            print("Usage: python odds.py [week_number]")
            print("Example: python odds.py 2")
            sys.exit(1)
    
    main(week=week)
