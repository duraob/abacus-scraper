from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
import os
import pickle
import hashlib
from datetime import datetime, timedelta
import time
import random
import logging

# Setup logging
logging.basicConfig(filename='scraper_errors.log', level=logging.ERROR)

def setupWebDriver():
    """
        SETUP CHROME DRIVER FOR SELENIUM
            Options: run in background / set log-level to show errors only / ignore certs for clean readability.
            Return - Driver
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Disable Chromium logging
    options.add_argument('--log-level=3')  # Set log level to only show severe errors
    options.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=options)
    return driver

def get_cache_path(url):
    """
    Generate a cache file path for a given URL
    """
    # Create a unique filename based on the URL
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join('cache', f'{url_hash}.pickle')

def is_cache_valid(cache_path, max_age_hours=24):
    """
    Check if the cache file exists and is not too old
    """
    if not os.path.exists(cache_path):
        return False
    
    file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
    age = datetime.now() - file_time
    return age < timedelta(hours=max_age_hours)

def get_soup(url, driver):
    """
    GET SOUP FROM URL
        First checks cache, then falls back to web request if needed
        Options: use driver to get soup from url
        Return - Soup
    """
    cache_path = get_cache_path(url)
    
    # Try to load from cache first
    if is_cache_valid(cache_path):
        try:
            print(f"Loading cached data for {url}")
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
    
    # If cache miss or error, fetch from web
    try:
        print(f"Fetching fresh data from {url}")
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Save to cache
        try:
            os.makedirs('cache', exist_ok=True)
            with open(cache_path, 'wb') as f:
                pickle.dump(soup, f)
        except Exception as e:
            print(f"Error saving to cache: {e}")
        
        return soup
    except Exception as e:
        print(f"Error getting soup from {url}: {e}")
        return None
    finally:
        driver.quit()

def get_game_links(soup):
    try:
        print("Getting game links")
        game_table = soup.select_one('table#games')
        game_links = game_table.select('a[href*="/boxscores/"]')
        return game_links
    except Exception as e:
        print(f"Error getting game links: {e}")
        return None
    
def get_game_data(driver, game_url, year):
    # Collect player data as a list of dicts for efficiency
    player_data = []
    soup = get_soup(game_url, driver)

    # Same Data Needed for all players:
    week = soup.select_one('div.game_summaries.compressed h2 a').get_text().split(' ')[1]
    weather = soup.select_one('table#game_info td[data-stat="stat"]', string=lambda x: 'Weather' in str(x.find_previous('th'))).get_text(strip=True) if soup else None
    home_team = soup.select_one('table#team_stats th[data-stat="home_stat"]').get_text(strip=True)
    away_team = soup.select_one('table#team_stats th[data-stat="vis_stat"]').get_text(strip=True)

    # Get scores from the 7th td (index 6) in the linescore table rows
    score_rows = soup.select('table.linescore tr')
    away_score = score_rows[1].select('td')[6].get_text(strip=True) if len(score_rows) > 0 else None
    home_score = score_rows[2].select('td')[6].get_text(strip=True) if len(score_rows) > 1 else None

    # Player Data:
    player_table = soup.select_one('table#player_offense')
    player_rows = player_table.select('tbody tr')
    for row in player_rows:
        if 'thead' in row.get('class', []):
            continue
        player_dict = {
            'year': year,
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
        # Snap count data
        team = player_dict['team']
        snap_table_id = "home_snap_counts" if team == home_team else "vis_snap_counts"
        snap_table = soup.select_one(f'table#{snap_table_id}')
        if snap_table:
            player_row = snap_table.find('a', string=lambda x: player_dict['player'] in str(x))
            if player_row:
                player_row = player_row.find_parent('tr')
                player_dict['pos'] = player_row.select_one('td[data-stat="pos"]').get_text(strip=True)
                player_dict['snaps'] = player_row.select_one('td[data-stat="offense"]').get_text(strip=True).rstrip('%')
                player_dict['snap_pct'] = player_row.select_one('td[data-stat="off_pct"]').get_text(strip=True).rstrip('%')
        player_data.append(player_dict)
    df = pd.DataFrame(player_data)
    return df

def safe_get_game_data(driver, game_url, year, max_retries=3):
    for attempt in range(max_retries):
        try:
            df = get_game_data(driver, game_url, year)
            print(f"Successfully retrieved: {game_url}")
            return df
        except Exception as e:
            logging.error(f"Attempt {attempt+1} failed for {game_url}: {e}")
            print(f"Error fetching {game_url}, attempt {attempt+1}/{max_retries}")
            time.sleep(random.uniform(2, 5))
    print(f"Max retries hit for {game_url}. Re-initializing web driver and retrying once more.")
    logging.error(f"Max retries hit for {game_url}. Re-initializing web driver and retrying once more.")
    # Re-initialize driver and try one more time
    new_driver = setupWebDriver()
    try:
        df = get_game_data(new_driver, game_url, year)
        print(f"Successfully retrieved after re-initializing driver: {game_url}")
        return df
    except Exception as e:
        print(f"Failed again after re-initializing driver for {game_url}. Exiting program.")
        logging.error(f"Failed again after re-initializing driver for {game_url}: {e}")
        exit(1)

if __name__ == "__main__":
    """
    SEASON GAME DATA WORKFLOW:
        Get all game data for a given year
        Save to csv
        Return df
    """
    YEAR = 2024
    BASE_URL = "https://www.pro-football-reference.com"
    SEASON_URL = BASE_URL + f"/years/{YEAR}/games.htm"

    driver = setupWebDriver()

    soup = get_soup(SEASON_URL, driver)
    game_links = get_game_links(soup)

    df_season = pd.DataFrame()
    if game_links and len(game_links) > 0:
        print(f"First game_link type: {type(game_links[0])}, value: {game_links[0]}")
    for link in game_links:
        # Handle both Tag and string cases
        if hasattr(link, 'attrs') and 'href' in link.attrs:
            game_url = BASE_URL + link['href']
        else:
            game_url = BASE_URL + str(link)
        print(f"Processing game_url: {game_url}")
        df_game = safe_get_game_data(driver, game_url, YEAR)
        if df_game is not None:
            df_season = pd.concat([df_season, df_game], ignore_index=True)
        # Best practice: wait between requests to avoid overwhelming the host
        time.sleep(random.uniform(5, 10))

    os.makedirs('data', exist_ok=True)
    df_season.to_csv(f'data/game_data_{YEAR}.csv', index=False)




