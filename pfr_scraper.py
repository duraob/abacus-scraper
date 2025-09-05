"""
Enhanced NFL Data Scraper - Undetected Chrome Driver
Optimized for weekly runs to capture fresh NFL data for projection engine.

This script uses undetected-chromedriver to avoid Cloudflare/bot detection
while scraping Pro Football Reference, providing a reliable fallback to API methods.
"""

import pandas as pd
import os
import pickle
import hashlib
from datetime import datetime, timedelta
import time
import random
import logging
import json
import requests
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nfl_data_enhanced.log'),
        logging.StreamHandler()
    ]
)

class EnhancedNFLScraper:
    def __init__(self, year=2025):
        self.year = year
        self.cache_dir = 'cache/current_season'
        self.data_dir = 'data/current_season'
        self.base_url = "https://www.pro-football-reference.com"
        
        # Create directories
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize driver as None
        self.driver = None
        
    def setup_undetected_driver(self):
        """Setup undetected Chrome driver to avoid bot detection"""
        try:
            logging.info("Setting up undetected Chrome driver...")
            
            # Use undetected-chromedriver with your installed Chrome
            options = uc.ChromeOptions()
            
            # Add options to make it more human-like
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Use simpler options that work with undetected-chromedriver
            self.driver = uc.Chrome(options=options, version_main=None)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logging.info("Undetected Chrome driver setup complete")
            return True
            
        except Exception as e:
            logging.error(f"Error setting up undetected driver: {e}")
            return False
    
    def get_cache_path(self, cache_key: str) -> str:
        """Generate cache file path for a given cache key"""
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f'{cache_hash}.pickle')
    
    def is_cache_valid(self, cache_path: str, max_age_hours: int = 24) -> bool:
        """Check if cache is valid"""
        if not os.path.exists(cache_path):
            return False
        
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        age = datetime.now() - file_time
        return age < timedelta(hours=max_age_hours)
    
    def get_cached_data(self, cache_key: str, cache_hours: int = 24) -> Tuple[Optional[object], bool]:
        """Get data from cache or return None if not available/valid"""
        cache_path = self.get_cache_path(cache_key)
        
        if self.is_cache_valid(cache_path, cache_hours):
            try:
                logging.info(f"Loading cached data for {cache_key}")
                with open(cache_path, 'rb') as f:
                    return pickle.load(f), True
            except Exception as e:
                logging.error(f"Error loading cache: {e}")
        
        return None, False
    
    def save_to_cache(self, cache_key: str, data: object) -> bool:
        """Save data to cache"""
        try:
            cache_path = self.get_cache_path(cache_key)
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            logging.error(f"Error saving to cache: {e}")
            return False
    
    def get_soup_with_undetected(self, url: str, cache_hours: int = 24) -> Tuple[Optional[BeautifulSoup], bool]:
        """Get BeautifulSoup object using undetected Chrome driver"""
        cache_key = f"undetected_{hashlib.md5(url.encode()).hexdigest()}"
        cached_soup, from_cache = self.get_cached_data(cache_key, cache_hours)
        
        if from_cache:
            return cached_soup, True
        
        if not self.driver:
            logging.error("Driver not initialized")
            return None, False
        
        try:
            logging.info(f"Fetching data from {url} using undetected Chrome")
            
            # Navigate to the page
            self.driver.get(url)
            
            # Wait for page to load (human-like delay)
            time.sleep(random.uniform(2, 4))
            
            # Check for Cloudflare protection
            page_title = self.driver.title.lower()
            if "just a moment" in page_title or "checking your browser" in page_title:
                logging.warning("Cloudflare protection detected, waiting...")
                time.sleep(random.uniform(10, 15))  # Wait longer for Cloudflare
                
                # Refresh and wait again
                self.driver.refresh()
                time.sleep(random.uniform(5, 8))
                
                # Check if still blocked
                page_title = self.driver.title.lower()
                if "just a moment" in page_title or "checking your browser" in page_title:
                    logging.error("Still blocked by Cloudflare protection")
                    return None, False
            
            # Get page source and create BeautifulSoup object
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Save to cache
            self.save_to_cache(cache_key, soup)
            
            logging.info(f"Successfully fetched data from {url}")
            return soup, False
            
        except Exception as e:
            logging.error(f"Error fetching data from {url}: {e}")
            return None, False
    
    def identify_current_week(self) -> Optional[int]:
        """Identify the current NFL week using the schedule CSV file"""
        cache_key = f"current_week_{self.year}"
        cached_week, from_cache = self.get_cached_data(cache_key, cache_hours=6)
        
        if from_cache:
            return cached_week
        
        try:
            logging.info(f"Identifying current week for {self.year} using schedule file")
            
            # Load the schedule CSV file
            schedule_file = f"data/nfl-{self.year}-EasternStandardTime.csv"
            if not os.path.exists(schedule_file):
                logging.error(f"Schedule file not found: {schedule_file}")
                return None
            
            # Read the schedule CSV
            schedule_df = pd.read_csv(schedule_file)
            
            # Convert date column to datetime
            schedule_df['Date'] = pd.to_datetime(schedule_df['Date'], format='%d/%m/%Y %H:%M', errors='coerce')
            
            # Get today's date
            today = datetime.now().date()
            
            # Find the current week
            current_week = None
            
            # Look for games today or in the future
            future_games = schedule_df[schedule_df['Date'].dt.date >= today]
            
            if not future_games.empty:
                # Get the week of the next game
                next_game = future_games.iloc[0]
                current_week = next_game['Round Number']
                game_date = next_game['Date'].date()
                
                logging.info(f"Found current week: {current_week} (next game: {game_date})")
            else:
                # If no future games, we're in the offseason, default to week 1
                current_week = 1
                logging.info("No future games found, defaulting to week 1")
            
            # Cache the result
            self.save_to_cache(cache_key, current_week)
            return current_week
                
        except Exception as e:
            logging.error(f"Error identifying current week: {e}")
            # Default to week 1 if there's any error
            return 1
    
    def get_current_week(self) -> Optional[int]:
        """Get the current NFL week"""
        return self.identify_current_week()
    
    def get_week_games(self, week: int) -> List[Dict]:
        """Get all games for a specific week using the schedule CSV file"""
        cache_key = f"week_games_{self.year}_{week}"
        cached_games, from_cache = self.get_cached_data(cache_key, cache_hours=12)
        
        if from_cache:
            return cached_games
        
        try:
            logging.info(f"Getting games for week {week} from schedule file")
            
            # Load the schedule CSV file
            schedule_file = f"data/nfl-{self.year}-EasternStandardTime.csv"
            if not os.path.exists(schedule_file):
                logging.error(f"Schedule file not found: {schedule_file}")
                return []
            
            # Read the schedule CSV
            schedule_df = pd.read_csv(schedule_file)
            
            # Filter games for the specified week
            week_games_df = schedule_df[schedule_df['Round Number'] == week]
            
            if week_games_df.empty:
                logging.warning(f"No games found for week {week}")
                return []
            
            week_games = []
            
            for _, game in week_games_df.iterrows():
                # Convert date to proper format
                game_date = pd.to_datetime(game['Date'], format='%d/%m/%Y %H:%M')
                
                # Create game info dictionary
                game_info = {
                    'week': week,
                    'date': game_date.strftime('%Y-%m-%d'),
                    'home_team': game['Home Team'],
                    'away_team': game['Away Team'],
                    'location': game['Location'],
                    'game_url': None,  # We don't have boxscore URLs from schedule
                    'home_score': None,  # Games haven't been played yet
                    'away_score': None,
                    'is_completed': False  # All games in schedule are upcoming
                }
                
                week_games.append(game_info)
                logging.info(f"Found game: {game['Away Team']} @ {game['Home Team']} ({game_date.strftime('%Y-%m-%d')})")
            
            # Cache the results
            self.save_to_cache(cache_key, week_games)
            logging.info(f"Found {len(week_games)} games for week {week}")
            return week_games
                
        except Exception as e:
            logging.error(f"Error getting week games: {e}")
            return []
    
    def parse_game_data(self, game_info: Dict) -> Optional[pd.DataFrame]:
        """Parse individual game data using undetected scraping"""
        cache_key = f"game_data_{hashlib.md5(game_info['game_url'].encode()).hexdigest()}"
        cached_data, from_cache = self.get_cached_data(cache_key, cache_hours=12)
        
        if from_cache:
            return cached_data
        
        try:
            logging.info(f"Parsing game data for {game_info['away_team']} @ {game_info['home_team']}")
            
            soup, from_cache = self.get_soup_with_undetected(game_info['game_url'], cache_hours=12)
            
            if not soup:
                return None
            
            # Check for Playoffs
            try:
                week_str = soup.select_one('div.game_summaries.compressed h2 a').get_text()
            except Exception as e:
                logging.error(f"Error parsing week string for {game_info['game_url']}: {e}")
                return None

            if "Playoffs" in week_str:
                logging.info(f"Skipping playoff game: {game_info['game_url']}")
                return None

            # Extract week info
            try:
                week = week_str.split(' ')[1]
            except Exception as e:
                logging.error(f"Error parsing week number for {game_info['game_url']}: {e}")
                week = None
            
            # Get weather info
            try:
                game_info_tbl = soup.select_one('table#game_info')
                th_weather = game_info_tbl.find('th', text="Weather")
                tr_with_weather = th_weather.find_parent('tr')
                weather = tr_with_weather.select_one('td').get_text(strip=True)
            except Exception as e:
                weather = "indoors"
                logging.info(f"Weather not found or error for {game_info['game_url']}: {e}")
            
            # Get teams
            try:
                home_team = soup.select_one('table#team_stats th[data-stat="home_stat"]').get_text(strip=True)
                away_team = soup.select_one('table#team_stats th[data-stat="vis_stat"]').get_text(strip=True)
            except Exception as e:
                logging.error(f"Error parsing teams for {game_info['game_url']}: {e}")
                return None
            
            # Get scores
            try:
                score_rows = soup.select('table.linescore tr')
                away_score = score_rows[1].select('td')[6].get_text(strip=True) if len(score_rows) > 0 else None
                home_score = score_rows[2].select('td')[6].get_text(strip=True) if len(score_rows) > 1 else None
            except Exception as e:
                logging.error(f"Error parsing scores for {game_info['game_url']}: {e}")
                away_score = None
                home_score = None
            
            # Parse player data
            try:
                player_table = soup.select_one('table#player_offense')
                player_rows = player_table.select('tbody tr')
            except Exception as e:
                logging.error(f"Error parsing player table for {game_info['game_url']}: {e}")
                return None
            
            player_data = []
            
            for row in player_rows:
                if 'thead' in row.get('class', []):
                    continue
                
                try:
                    player_dict = {
                        'year': self.year,
                        'week': week,
                        'weather': weather,
                        'home_team': home_team,
                        'away_team': away_team,
                        'player': row.select_one('th[data-stat="player"] a').get_text(strip=True) if row.select_one('th[data-stat="player"] a') else None,
                        'team': row.select_one('td[data-stat="team"]').get_text(strip=True),
                        'opponent': home_team if row.select_one('td[data-stat="team"]').get_text(strip=True) == away_team else away_team,
                        'home_away': "home" if row.select_one('td[data-stat="team"]').get_text(strip=True) == home_team else "away",
                        'team_score': home_score if row.select_one('td[data-stat="team"]').get_text(strip=True) == home_team else away_score,
                        'opp_score': away_score if row.select_one('td[data-stat="team"]').get_text(strip=True) == home_team else home_score,
                        'pos': None,
                        'snaps': None,
                        'snap_pct': None,
                        'pass_cmp': row.select_one('td[data-stat="pass_cmp"]').get_text(strip=True),
                        'pass_att': row.select_one('td[data-stat="pass_att"]').get_text(strip=True),
                        'pass_yds': row.select_one('td[data-stat="pass_yds"]').get_text(strip=True),
                        'pass_tds': row.select_one('td[data-stat="pass_td"]').get_text(strip=True),
                        'pass_int': row.select_one('td[data-stat="pass_int"]').get_text(strip=True),
                        'sacks': row.select_one('td[data-stat="pass_sacked"]').get_text(strip=True),
                        'rush_att': row.select_one('td[data-stat="rush_att"]').get_text(strip=True),
                        'rush_yds': row.select_one('td[data-stat="rush_yds"]').get_text(strip=True),
                        'rush_tds': row.select_one('td[data-stat="rush_td"]').get_text(strip=True),
                        'targets': row.select_one('td[data-stat="targets"]').get_text(strip=True),
                        'receptions': row.select_one('td[data-stat="rec"]').get_text(strip=True),
                        'rec_yds': row.select_one('td[data-stat="rec_yds"]').get_text(strip=True),
                        'rec_tds': row.select_one('td[data-stat="rec_td"]').get_text(strip=True),
                        'fumbles': row.select_one('td[data-stat="fumbles"]').get_text(strip=True)
                    }
                    
                    # Get snap count data if available
                    team = player_dict['team']
                    snap_table_id = "home_snap_counts" if team == home_team else "vis_snap_counts"
                    snap_table = soup.select_one(f'table#{snap_table_id}')
                    if snap_table:
                        player_row = snap_table.find('a', string=lambda x: player_dict['player'] in str(x))
                        if player_row:
                            player_row = player_row.find_parent('tr')
                            if player_row:
                                pos_cell = player_row.select_one('td[data-stat="pos"]')
                                snaps_cell = player_row.select_one('td[data-stat="offense"]')
                                snap_pct_cell = player_row.select_one('td[data-stat="off_pct"]')
                                
                                if pos_cell:
                                    player_dict['pos'] = pos_cell.get_text(strip=True)
                                if snaps_cell:
                                    player_dict['snaps'] = snaps_cell.get_text(strip=True).rstrip('%')
                                if snap_pct_cell:
                                    player_dict['snap_pct'] = snap_pct_cell.get_text(strip=True).rstrip('%')
                    
                    player_data.append(player_dict)
                    
                except Exception as e:
                    logging.error(f"Error parsing player row: {e}")
                    continue
            
            if player_data:
                df = pd.DataFrame(player_data)
                
                # Cache the result
                self.save_to_cache(cache_key, df)
                return df
            else:
                logging.warning(f"No player data found for game {game_info['game_url']}")
                return None
            
        except Exception as e:
            logging.error(f"Error parsing game data: {e}")
            return None
    
    def get_previous_week_results(self, week: int) -> Optional[pd.DataFrame]:
        """Get completed game results from previous week"""
        logging.info(f"Getting previous week {week} results...")
        
        week_games = self.get_week_games(week)
        
        if not week_games:
            logging.warning(f"No games found for week {week}")
            return None
        
        # Since we're working with schedule data, all games are upcoming (not completed)
        # For now, return None since we don't have completed game data
        logging.info(f"Found {len(week_games)} games for week {week}, but they are upcoming games (not completed)")
        logging.info("Note: This method is designed for completed game results, but we're working with schedule data")
        
        # Return empty DataFrame with expected columns for compatibility
        empty_df = pd.DataFrame(columns=[
            'year', 'week', 'weather', 'home_team', 'away_team', 'player', 'team', 
            'opponent', 'home_away', 'team_score', 'opp_score', 'pos', 'snaps', 
            'snap_pct', 'pass_cmp', 'pass_att', 'pass_yds', 'pass_tds', 'pass_int', 
            'sacks', 'rush_att', 'rush_yds', 'rush_tds', 'targets', 'receptions', 
            'rec_yds', 'rec_tds', 'fumbles'
        ])
        
        return empty_df
    
    def get_current_week_matchups(self, week: int) -> List[Dict]:
        """Get current week matchups for projections"""
        logging.info(f"Getting current week {week} matchups...")
        
        week_games = self.get_week_games(week)
        
        if not week_games:
            logging.warning(f"No upcoming games found for week {week}")
            return []
        
        # All games in the schedule are upcoming games
        upcoming_games = week_games
        
        logging.info(f"Found {len(upcoming_games)} upcoming games for week {week}")
        return upcoming_games
    
    def collect_weekly_data(self) -> Dict:
        """Main method to collect data for projection engine"""
        logging.info(f"Starting weekly data collection for {self.year}")
        
        try:
            # Setup undetected driver
            if not self.setup_undetected_driver():
                logging.error("Failed to setup undetected driver")
                return {}
            
            # Identify current week
            current_week = self.identify_current_week()
            if not current_week:
                logging.error("Could not identify current week")
                return {}
            
            # Get previous week results
            previous_week = current_week - 1
            previous_results = None
            if previous_week > 0:
                previous_results = self.get_previous_week_results(previous_week)
            
            # Get current week matchups
            current_matchups = self.get_current_week_matchups(current_week)
            
            # Save data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if previous_results is not None and not previous_results.empty:
                previous_file = f"previous_week_{previous_week}_{timestamp}.csv"
                previous_path = os.path.join(self.data_dir, previous_file)
                previous_results.to_csv(previous_path, index=False)
                logging.info(f"Saved previous week results to {previous_path}")
            
            if current_matchups:
                matchups_file = f"current_week_{current_week}_matchups_{timestamp}.json"
                matchups_path = os.path.join(self.data_dir, matchups_file)
                with open(matchups_path, 'w') as f:
                    json.dump(current_matchups, f, indent=2)
                logging.info(f"Saved current week matchups to {matchups_path}")
            
            return {
                'current_week': current_week,
                'previous_week': previous_week,
                'previous_results': previous_results,
                'current_matchups': current_matchups,
                'data_quality': {
                    'previous_records': len(previous_results) if previous_results is not None else 0,
                    'upcoming_games': len(current_matchups),
                    'scrape_timestamp': timestamp
                }
            }
            
        except Exception as e:
            logging.error(f"Error in collect_weekly_data: {e}")
            return {}
        finally:
            if self.driver:
                self.driver.quit()
    
    def scrape_current_week(self):
        """Legacy method for backward compatibility"""
        data = self.collect_weekly_data()
        if data.get('previous_results') is not None:
            return data['previous_results']
        return None

def main():
    """Main execution function"""
    scraper = EnhancedNFLScraper(year=2025)
    data = scraper.collect_weekly_data()
    
    if data:
        print(f"✅ Enhanced data collection successful!")
        print(f"Current Week: {data.get('current_week', 'Unknown')}")
        print(f"Previous Week Records: {data.get('data_quality', {}).get('previous_records', 0)}")
        print(f"Upcoming Games: {data.get('data_quality', {}).get('upcoming_games', 0)}")
        print(f"Data saved to {scraper.data_dir}")
    else:
        print("❌ Enhanced data collection failed")

if __name__ == "__main__":
    main()
