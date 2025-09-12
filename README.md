# Abacus Scraper - NFL Data Collection System

This application is a comprehensive NFL data scraping system that collects various types of football data for analysis and projection purposes.

## What This Application Does

The Abacus Scraper is designed to automatically collect NFL data from multiple sources to help with fantasy football analysis and projections. It's like having a digital assistant that visits NFL websites and gathers all the important information for you.

## Main Components

### 1. NFL Data Scraper (`nfl_data.py`)
- **What it does**: Collects detailed player statistics from Pro Football Reference
- **How it works**: Uses a special web browser (undetected Chrome) to visit the website and extract game data
- **What you get**: Complete player stats including passing, rushing, receiving, and team information
- **When to use**: Run this weekly to get fresh game data for the current season

### 2. Injuries Scraper (`injuries.py`) - NEW!
- **What it does**: Collects current injury information for all NFL players
- **How it works**: Visits ESPN's injury page and extracts player injury status
- **What you get**: Player names, positions, injury status, expected return dates, and detailed comments
- **Team Mapping**: Automatically converts full team names to standard abbreviations (ARI, ATL, BAL, etc.)
- **When to use**: Run this daily or weekly to stay updated on player injuries

### 3. Projection Engine (`projection.py`)
- **What it does**: Creates fantasy football projections using historical data and injury information
- **How it works**: Analyzes player performance, team matchups, and schedule strength
- **Injury Integration**: Automatically excludes players who are "Out" or "Injured Reserve" from projections
- **What you get**: Weekly player projections with realistic expectations based on availability
- **When to use**: Run weekly to get updated projections for the current week

### 4. Other Components
- **Stats Analysis**: Processes and analyzes the scraped data
- **Telegram Bot**: Sends updates and insights via messaging

## How to Use the Injuries Scraper

### Prerequisites
Make sure you have the virtual environment activated:
```bash
.venv\Scripts\Activate.ps1
```

### Running the Injuries Scraper
```bash
python injuries.py
```

### What Happens When You Run It
1. The program opens a web browser (you won't see it)
2. It visits ESPN's NFL injuries page
3. It finds all 32 NFL teams and their injury lists
4. It extracts information for each injured player:
   - Player name
   - Position (QB, RB, WR, etc.)
   - Expected return date
   - Current status (Questionable, Out, Injured Reserve, etc.)
   - Detailed injury comments
5. It saves all this data to a CSV file in the `data/` folder

### Output
The scraper creates a file like `data/injuries_20250912_113829.csv` with all the injury data. You can open this file in Excel or any spreadsheet program to view the information.

### Example Data
The CSV file contains columns like:
- **team**: NFL team abbreviation (ARI, ATL, BAL, etc.) - automatically converted from full names
- **name**: Player's name
- **pos**: Player's position
- **est_return_date**: When they might return
- **status**: Current injury status
- **comment**: Detailed injury information
- **scraped_date**: When the data was collected

## Testing the Latest Features

### Testing the Injuries Scraper

1. **Activate the virtual environment**:
   ```bash
   .venv\Scripts\Activate.ps1
   ```

2. **Run the scraper**:
   ```bash
   python injuries.py
   ```

3. **Check the results**:
   - Look for `data/injuries.csv` file
   - The program will tell you how many injury records were found
   - You should see data for all 32 NFL teams

4. **Verify the data**:
   - Open the CSV file in Excel or a text editor
   - Check that you see player names, positions, and injury information
   - Verify that all 32 teams are represented

### Testing the Projection Engine with Injury Filtering

1. **Run the projection engine**:
   ```bash
   python projection.py 2
   ```

2. **Check the output**:
   - The program will show how many injured players were excluded
   - Look for messages like "Excluded 255 injured players from active roster"
   - Final projections will only include available players

3. **Verify injury filtering**:
   - Check `data/projections/nfl25_proj_week1.csv`
   - Injured players should not appear in the projections
   - Only healthy, available players should have projections

## Important Notes

- The scraper uses a special browser that avoids detection by websites
- It includes delays to be respectful to the website
- Data is cached to avoid repeated requests
- The program handles errors gracefully and logs what it's doing

## File Structure

```
abacus-scraper/
├── data/                    # All collected data goes here
│   ├── injuries_*.csv      # Injury data files
│   ├── game_data_*.csv     # Game statistics
│   └── other data files
├── injuries.py             # NEW: Injuries scraper
├── nfl_data.py            # Main NFL data scraper
├── other Python files     # Additional components
└── README.md              # This file
```

This system helps you stay informed about NFL player injuries and game statistics automatically, making it easier to make informed decisions for fantasy football or general NFL analysis.
