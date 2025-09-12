"""
NFL Injuries Scraper
Scrapes injury data from ESPN NFL injuries page and saves to CSV.

This script uses undetected-chromedriver to avoid bot detection while scraping
ESPN's NFL injuries page, providing reliable injury data collection.
"""

import pandas as pd
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import time
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('injuries_scraper.log'),
        logging.StreamHandler()
    ]
)

# Configuration
INJURIES_URL = "https://www.espn.com/nfl/injuries"
DATA_DIR = 'data'
CACHE_HOURS = 6  # Cache for 6 hours since injury data changes frequently

# Create data directory
os.makedirs(DATA_DIR, exist_ok=True)


def load_team_mapping() -> Dict[str, str]:
    """
    Load team name to abbreviation mapping from Excel file.
    
    Returns:
        Dict[str, str]: Dictionary mapping full team names to abbreviations
    """
    try:
        team_map_path = os.path.join(DATA_DIR, 'team_map.xlsx')
        if not os.path.exists(team_map_path):
            logging.warning(f"Team mapping file not found at {team_map_path}")
            return {}
        
        df = pd.read_excel(team_map_path)
        team_mapping = dict(zip(df['full_team_name'], df['team_abbrev']))
        
        logging.info(f"Loaded team mapping for {len(team_mapping)} teams")
        return team_mapping
        
    except Exception as e:
        logging.error(f"Error loading team mapping: {e}")
        return {}


def setup_undetected_driver() -> Optional[uc.Chrome]:
    """
    Setup undetected Chrome driver to avoid bot detection.
    
    Returns:
        uc.Chrome: Configured Chrome driver or None if setup fails
    """
    try:
        logging.info("Setting up undetected Chrome driver...")
        
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)
        
        logging.info("Undetected Chrome driver setup complete")
        return driver
        
    except Exception as e:
        logging.error(f"Error setting up undetected driver: {e}")
        return None


def get_injuries_page(driver: uc.Chrome) -> Optional[BeautifulSoup]:
    """
    Retrieve the ESPN NFL injuries page and return BeautifulSoup object.
    
    Args:
        driver: Configured Chrome driver
        
    Returns:
        BeautifulSoup: Parsed HTML content or None if failed
    """
    try:
        logging.info(f"Fetching injuries page from {INJURIES_URL}")
        
        driver.get(INJURIES_URL)
        time.sleep(random.uniform(3, 5))  # Human-like delay
        
        # Check for any blocking
        page_title = driver.title.lower()
        if "just a moment" in page_title or "checking your browser" in page_title:
            logging.warning("Potential blocking detected, waiting...")
            time.sleep(random.uniform(10, 15))
            driver.refresh()
            time.sleep(random.uniform(5, 8))
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        if not soup or len(page_source) < 1000:
            logging.error("Got invalid content from injuries page")
            return None
        
        logging.info("Successfully retrieved injuries page")
        return soup
        
    except Exception as e:
        logging.error(f"Error fetching injuries page: {e}")
        return None


def extract_team_name_from_table_title(table_title_element) -> str:
    """
    Extract team name from table title element.
    
    Args:
        table_title_element: BeautifulSoup element containing table title
        
    Returns:
        str: Team name or empty string if not found
    """
    try:
        # Look for team name in span with class 'injuries__teamName' (double underscore)
        team_name_span = table_title_element.find('span', class_='injuries__teamName')
        if team_name_span:
            return team_name_span.get_text().strip()
        
        # Fallback: look for team name in img title attribute
        team_img = table_title_element.find('img', class_='Logo')
        if team_img and team_img.get('title'):
            return team_img.get('title').strip()
        
        return ""
        
    except Exception as e:
        logging.warning(f"Error extracting team name: {e}")
        return ""


def extract_injury_data_from_table(table, team_name: str) -> List[Dict]:
    """
    Extract injury data from a single team's injury table.
    
    Args:
        table: BeautifulSoup table element
        team_name: Name of the team
        
    Returns:
        List[Dict]: List of injury records for the team
    """
    injuries = []
    
    try:
        # Find table body
        tbody = table.find('tbody', class_='Table__TBODY')
        if not tbody:
            logging.warning(f"No tbody found for team {team_name}")
            return injuries
        
        rows = tbody.find_all('tr', class_='Table__TR')
        logging.info(f"Found {len(rows)} injury rows for {team_name}")
        
        for row in rows:
            try:
                cells = row.find_all('td', class_='Table__TD')
                if len(cells) < 5:  # Need at least 5 columns for injury data
                    continue
                
                # Extract data from cells
                # Based on ESPN structure: Name, Pos, Est. Return Date, Status, Comment
                name = cells[0].get_text().strip() if len(cells) > 0 else ""
                pos = cells[1].get_text().strip() if len(cells) > 1 else ""
                est_return = cells[2].get_text().strip() if len(cells) > 2 else ""
                status = cells[3].get_text().strip() if len(cells) > 3 else ""
                comment = cells[4].get_text().strip() if len(cells) > 4 else ""
                
                # Skip empty rows
                if not name:
                    continue
                
                injury_record = {
                    'team': team_name,
                    'name': name,
                    'pos': pos,
                    'est_return_date': est_return,
                    'status': status,
                    'comment': comment,
                    'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                injuries.append(injury_record)
                logging.debug(f"Added injury: {name} ({pos}) - {status}")
                
            except Exception as e:
                logging.warning(f"Error processing injury row: {e}")
                continue
        
        logging.info(f"Extracted {len(injuries)} injuries for {team_name}")
        return injuries
        
    except Exception as e:
        logging.error(f"Error extracting injury data for {team_name}: {e}")
        return []


def parse_injuries_data(soup: BeautifulSoup) -> List[Dict]:
    """
    Parse all injury data from the ESPN injuries page.
    
    Args:
        soup: BeautifulSoup object of the injuries page
        
    Returns:
        List[Dict]: All injury records from all teams
    """
    all_injuries = []
    
    try:
        # Find all table titles (each represents a team's injury table)
        # ESPN uses 'Table__Title' class (double underscore)
        table_titles = soup.find_all('div', class_='Table__Title')
        logging.info(f"Found {len(table_titles)} team injury tables")
        
        for title_element in table_titles:
            try:
                # Extract team name from table title
                team_name = extract_team_name_from_table_title(title_element)
                if not team_name:
                    logging.warning("Could not extract team name from table title")
                    continue
                
                logging.info(f"Processing injuries for {team_name}")
                
                # Find the corresponding table for this team
                # The table is in a sibling div with class 'Table__Scroller'
                table_scroller = title_element.find_next_sibling('div', class_='Table__ScrollerWrapper')
                if not table_scroller:
                    # Try finding in parent container
                    parent = title_element.parent
                    if parent:
                        table_scroller = parent.find('div', class_='Table__ScrollerWrapper')
                
                if not table_scroller:
                    logging.warning(f"No table scroller found for {team_name}")
                    continue
                
                # Find the actual table within the scroller
                table = table_scroller.find('table', class_='Table')
                if not table:
                    logging.warning(f"No injury table found for {team_name}")
                    continue
                
                # Extract injury data from this team's table
                team_injuries = extract_injury_data_from_table(table, team_name)
                all_injuries.extend(team_injuries)
                
            except Exception as e:
                logging.error(f"Error processing team injuries: {e}")
                continue
        
        logging.info(f"Total injuries extracted: {len(all_injuries)}")
        return all_injuries
        
    except Exception as e:
        logging.error(f"Error parsing injuries data: {e}")
        return []


def save_injuries_to_csv(injuries: List[Dict]) -> str:
    """
    Save injury data to CSV file in the data directory.
    
    Args:
        injuries: List of injury dictionaries
        
    Returns:
        str: Path to saved CSV file
    """
    try:
        if not injuries:
            logging.warning("No injury data to save")
            return ""
        
        # Create DataFrame
        df = pd.DataFrame(injuries)
        
        # Generate filename with timestamp
        filename = f"injuries.csv"
        filepath = os.path.join(DATA_DIR, filename)
        
        # Save to CSV
        df.to_csv(filepath, index=False)
        
        logging.info(f"Injury data saved to {filepath}")
        logging.info(f"Saved {len(injuries)} injury records")
        
        return filepath
        
    except Exception as e:
        logging.error(f"Error saving injuries to CSV: {e}")
        return ""


def scrape_nfl_injuries() -> pd.DataFrame:
    """
    Main function to scrape NFL injury data from ESPN.
    
    Returns:
        pd.DataFrame: Complete injury data with team abbreviations
    """
    start_time = datetime.now()
    logging.info("Starting NFL injuries scrape")
    
    driver = None
    try:
        # Load team mapping
        team_mapping = load_team_mapping()
        if not team_mapping:
            logging.warning("No team mapping loaded, will use full team names")
        
        # Setup driver
        driver = setup_undetected_driver()
        if not driver:
            logging.error("Failed to setup Chrome driver")
            return pd.DataFrame()
        
        # Get injuries page
        soup = get_injuries_page(driver)
        if not soup:
            logging.error("Failed to retrieve injuries page")
            return pd.DataFrame()
        
        # Parse injury data
        injuries = parse_injuries_data(soup)
        if not injuries:
            logging.warning("No injury data found")
            return pd.DataFrame()
        
        # Convert team names to abbreviations if mapping is available
        if team_mapping:
            for injury in injuries:
                full_name = injury['team']
                if full_name in team_mapping:
                    injury['team'] = team_mapping[full_name]
                    logging.debug(f"Converted {full_name} to {team_mapping[full_name]}")
                else:
                    logging.warning(f"No abbreviation found for team: {full_name}")
        
        # Convert to DataFrame
        df = pd.DataFrame(injuries)
        
        # Save to CSV
        csv_file = save_injuries_to_csv(injuries)
        if csv_file:
            logging.info(f"Data saved to {csv_file}")
        
        return df
        
    except Exception as e:
        logging.error(f"Error during injuries scraping: {e}")
        return pd.DataFrame()
    
    finally:
        if driver:
            try:
                driver.close()
                driver.quit()
                logging.info("Chrome driver closed")
            except Exception as e:
                logging.warning(f"Error closing driver: {e}")
    
    end_time = datetime.now()
    logging.info(f"Injuries scraping completed in {end_time - start_time}")


def main():
    """
    Main entry point for the injuries scraper.
    """
    logging.info("Starting NFL injuries scraper")
    
    # Scrape injury data
    df = scrape_nfl_injuries()
    
    if not df.empty:
        print(f"Successfully scraped {len(df)} injury records")
        print(f"Teams covered: {df['team'].nunique()}")
        print(f"Data saved to data/ directory")
    else:
        logging.error("No injury data was scraped")
        print("No injury data was scraped. Check logs for errors.")


if __name__ == "__main__":
    main()
