# PFR Scraper

A Python-based web scraper for Pro Football Reference data.

## Features

- Web scraping using Selenium and BeautifulSoup4
- Local caching system to reduce website requests during testing
- Modular and reusable functions for common scraping tasks
- **NEW**: NFL Projection Engine with schedule strength normalization
- **NEW**: NFL Fun Stats Agent for generating focused, odds-aligned insights

## Recent Bug Fixes

### Column Naming Issue (Fixed)
**Problem**: The projection engine was failing with a `KeyError: 'int'` because it was trying to access a column named `int` that didn't exist. The actual column name was `pass_int`.

**Solution**: Updated all references from `int` to `pass_int` throughout the `analyze()` function in `nfl_proj.py`. This ensures consistency with the actual column names in the game data.

**Files Modified**: `nfl_proj.py` - Lines 379, 400, 444

### Pandas FutureWarning (Fixed)
**Problem**: The code was using deprecated `fillna(0.0, inplace=True)` syntax, which triggered a FutureWarning about downcasting object dtype arrays.

**Solution**: Updated all `fillna()` calls to use the non-deprecated syntax: `df = df.fillna(0.0)` instead of `df.fillna(0.0, inplace=True)`.

**Files Modified**: `nfl_proj.py` - Lines 275, 276, 427, 461

## Caching System

The scraper includes a file-based caching system that:
- Stores scraped data in a `cache` directory
- Uses MD5 hashes of URLs as unique cache file names
- Automatically expires cache after 24 hours
- Falls back to live web requests if cache is missing or expired

## Data Collection Efficiency

Player data is now collected using a list of dictionaries and converted to a DataFrame at the end of scraping. This approach is more efficient and avoids the deprecated `pandas.DataFrame.append` method.

## NFL Projection Engine

The project now includes an NFL projection engine (`nfl_proj.py`) that can process the scraped game data to create fantasy football projections. The engine includes:

### Key Functions
- **`load_active_roster()`**: Loads and cleans active roster data, removing injury/status suffixes
- **`build_team_opponents_schedule()`**: Creates team schedule mapping with opponents list for schedule strength calculation
- **`build_team_statistics()`**: Aggregates player-level data to team-level offensive and defensive statistics
- **`create_team_dataset_from_game_data()`**: Creates complete team dataset compatible with the existing projection engine
- **`create_player_dataset_from_game_data()`**: Creates player dataset from game data for projections (active roster only)

### Usage

#### Process Game Data and Create Projections
```bash
# Process 2024 game data (default)
python nfl_proj.py --game-data

# Process specific game data file
python nfl_proj.py --game-data data/game_data_2024.csv

# Process game data with schedule for next opponent determination
python nfl_proj.py --game-data data/game_data_2024.csv nfl2025sched.csv 5

# Run with existing team/player data (legacy mode)
python nfl_proj.py
```

#### What It Does
1. **Loads active roster** from `data/master_roster.xlsx` and cleans player names (removes injury/status suffixes)
2. **Loads game data** from the CSV file created by the scraper
3. **Filters players** to only include those on the active roster (eliminates noise from inactive/injured players)
4. **Creates team datasets** with the "opps" column containing lists of opponents for schedule strength normalization
5. **Determines next opponents** using schedule data and current week (when provided)
6. **Aggregates player statistics** across all games for active players only
7. **Runs the projection engine** to calculate fantasy football projections based on schedule strength
8. **Saves processed datasets** as `nfl25_team.csv` and `nfl25_players.csv` for future use
9. **Logs filtering statistics** showing how many players were filtered out and why

#### Schedule Strength Normalization
The engine creates an "opps" column that lists all opponents each team has faced. This enables:
- **Schedule strength calculation**: Normalize team statistics based on the quality of opponents faced
- **Fantasy projections**: Adjust player projections based on upcoming opponent strength
- **League comparisons**: Compare team performance against league averages

#### Next Opponent Determination
When schedule data is provided, the engine determines each team's next opponent:
- **Schedule-based**: Uses the schedule CSV file to find future games
- **Week-aware**: Respects current week to find next upcoming game
- **Bye week handling**: Teams with no future games are marked as on bye
- **Projection accuracy**: Enables more accurate fantasy projections by considering opponent strength

## NFL Betting Picks Agent with AI Analysis

The project includes an advanced betting picks agent (`picks_agent.py`) that combines mathematical edge calculations with AI-powered contextual analysis using Grok AI.

### Features
- **AI-Powered Analysis**: Uses Grok AI for intelligent betting recommendations based on context
- **Live Search Integration**: Real-time web search for injuries, news, and expert insights
- **Accurate Team Mapping**: Uses master roster data for precise player-team-opponent relationships
- **Historical Performance Analysis**: Analyzes player performance vs specific opponents and recent form
- **Weather & Matchup Context**: Incorporates weather conditions and historical matchup data
- **Edge Calculation**: Calculates betting edge percentage using projection vs. line comparison
- **Standard Deviation Analysis**: Uses statistical variance to determine confidence levels
- **Comprehensive Player Mapping**: Automatically matches 339+ players across all NFL teams
- **X.AI SDK Integration**: Uses official X.AI SDK with live search capabilities
- **Weekly Organization**: Saves AI insights to `data/insights/` directory by week
- **Result Tracking**: Stores both raw data and AI analysis for performance tracking

### AI Analysis Process
1. **Context Building**: Creates comprehensive player context including:
   - Current projections vs betting lines
   - Historical performance vs specific opponents (using accurate team mapping)
   - Recent form and snap percentage trends
   - Weather conditions from similar games
   - Mathematical edge calculations

2. **Team Mapping**: Uses master roster data for accurate opponent determination:
   - Loads player-team relationships from master_roster.xlsx
   - Determines correct opposing teams for historical analysis
   - Ensures accurate matchup context for AI analysis

3. **Live Search Integration**: Gathers real-time information for unique players (optimized to avoid duplicates):
   - Injury status from NFL.com/injuries
   - Recent news from ESPN.com/nfl and NFL.com/news
   - Expert insights from RapSheet and AdamSchefter
   - Current weather conditions
   - Role changes and lineup adjustments
   - **Efficient caching**: Reuses search results for players with multiple props

4. **AI Analysis**: Sends enhanced context to Grok AI with live search:
   - Analyzes top 25 betting opportunities with 8%+ edge
   - Considers historical data + real-time information
   - Returns top 10 recommendations with reasoning
   - Provides confidence levels and risk assessment

5. **Intelligent Recommendations**: Grok AI provides:
   - Player name and prop recommendation
   - Over/Under/Yes/No direction
   - Confidence level (High/Medium/Low)
   - Key reasoning (2-3 sentences)
   - Risk factors and concerns

### Configuration
The agent uses these adjustable parameters:
- **`STD_DEV_THRESHOLD = 1.5`**: Standard deviations required for confidence (1.5 = 87% confidence)
- **`MIN_EDGE_PERCENTAGE = 8.0`**: Minimum edge percentage to consider a bet
- **`CONFIDENCE_THRESHOLDS`**: High/Medium/Low confidence levels

### API Setup
To use the AI analysis, install the X.AI SDK and set your API key:

```bash
# Install X.AI SDK
pip install xai-sdk

# Set environment variable
export GROK_API_KEY="your_grok_api_key_here"
```

### Usage
```bash
# Run AI analysis for current week
python picks_agent.py

# Run traditional analysis (no AI)
python -c "from picks_agent import main; main(1, use_ai=False)"

# Test system functionality
python test_ai_system.py
```

### Output Files
- **AI Insights**: `data/insights/grok_insights_week_XX.json` - Complete AI analysis with live search context
- **Traditional Picks**: `data/agent_picks/week_XX_picks.csv` - Mathematical edge analysis
- **Test Results**: System test results for dependency verification

### Data Sources
- **Master Roster**: `data/master_roster.xlsx` - Player-team mappings for accurate opponent determination
- **Team Mapping**: `data/team_map.xlsx` - Full team names to abbreviation mappings
- **Player Mapping**: `data/player_name_mapping.csv` - Odds names to projection names mappings
- **Live Search Sources**:
  - **NFL.com/injuries**: Official injury reports and practice participation
  - **ESPN.com/nfl**: Latest news and developments
  - **NFL.com/news**: Official team and player updates
  - **RapSheet**: Expert analysis and insider information
  - **AdamSchefter**: Breaking news and expert insights

## NFL Prop Nugget Module

The project now includes a prop nugget module (`stats_agent.py`) that generates statistical insights by comparing historical player performance against current betting lines.

### Features
- **Historical Data Analysis**: Processes 9 seasons of NFL game data (2016-2024)
- **Player Filtering**: Only analyzes props for players with sufficient historical data (minimum 3 games)
- **Statistical Trends**: Calculates career averages, recent form, and opponent-specific performance
- **Prop Type Mapping**: Automatically maps betting prop types to corresponding historical statistics
- **Insight Generation**: Creates structured nuggets with delta percentages and sample sizes
- **Quality Filtering**: Applies minimum thresholds for sample size (3+ games) and edge percentage (15%+)
- **LLM Integration**: Prepares data for AI analysis with ESPN-style writing prompts
- **GROK API Integration**: Automatically calls GROK API for ESPN-style betting insights
- **Weekly Organization**: Saves nuggets and insights to organized weekly directories

### How It Works
1. **Data Loading**: Loads historical game stats, current schedule, and player prop lines
2. **Player Matching**: Uses player name mapping to connect odds data with historical records
3. **Trend Analysis**: Computes career averages and recent performance trends for each player
4. **Nugget Generation**: Creates statistical insights comparing historical performance to prop lines
5. **Quality Filtering**: Applies statistical thresholds to ensure meaningful insights
6. **LLM Preparation**: Formats data for AI analysis with pre-defined ESPN-style prompts
7. **GROK API Call**: Automatically calls GROK API for ESPN-style betting insights
8. **Insights Storage**: Saves both raw nuggets and AI-generated insights

### Configuration
To use the GROK API integration, create a `.env` file in your project root:

```bash
# .env file
GROK_API_KEY=your_grok_api_key_here
```

### Usage
```bash
# Generate nuggets for Week 1
python stats_agent.py

# The module will:
# - Load all historical game data (2016-2024)
# - Filter props to players with sufficient data
# - Generate statistical insights
# - Save nuggets to data/nuggets/nuggets_week_01.json
# - Call GROK API for ESPN-style insights
# - Save AI insights to data/insights/grok_insights_week_01.json
```

### Output
- **JSON Nuggets**: Structured data with player stats, prop lines, and delta percentages
- **LLM Prompts**: Ready-to-use prompts for AI analysis of betting insights
- **GROK Insights**: ESPN-style betting insights generated by GROK AI
- **Statistical Validation**: Only includes insights meeting quality thresholds
- **Dual Storage**: Saves both raw data and AI-generated insights for analysis

### How It Works
1. **Loads Data**: Combines player projections with current week odds
2. **Calculates Edges**: Determines mathematical advantage for each prop bet
3. **Filters by Confidence**: Only shows bets meeting edge and standard deviation thresholds
4. **Generates Analysis**: Creates comprehensive prompt for Grok AI analysis
5. **Saves Results**: Stores weekly picks in organized CSV format

### Configuration
The agent uses these adjustable parameters:
- **`STD_DEV_THRESHOLD = 1.5`**: Standard deviations required for confidence (1.5 = 87% confidence)
- **`MIN_EDGE_PERCENTAGE = 8.0`**: Minimum edge percentage to consider a bet
- **`CONFIDENCE_THRESHOLDS`**: High/Medium/Low confidence levels

### Usage
```bash
# Analyze Week 1 (default)
python picks_agent.py

# Analyze specific week
python -c "from picks_agent import main; main(2)"
```

## NFL Odds Scraper

The project includes an NFL odds scraper (`odds_scraper.py`) that collects betting odds data from The Odds API and organizes it by NFL week.

### Features
- **API Integration**: Connects to The Odds API for real-time odds data
- **Weekly Organization**: Automatically organizes data into weekly folders based on NFL schedule
- **Comprehensive Data**: Collects both team odds (spreads, totals, moneyline) and player props
- **Smart Week Detection**: Determines current NFL week by comparing dates against the schedule

### Weekly Organization System
The odds scraper automatically creates a structured directory system:

```
data/
  odds/
    week_01/
      team_odds_week_01.csv
      player_props_week_01.csv
    week_02/
      team_odds_week_02.csv
      player_props_week_02.csv
    ...
```

### Key Functions
- **`get_current_nfl_week()`**: Determines the current NFL week based on schedule and current date
- **`get_weekly_directory()`**: Creates and returns the path to the appropriate weekly directory
- **`scrape_current_week_odds()`**: Main method that scrapes odds and saves them to weekly folders

### Usage
```bash
# Run the odds scraper
python odds_scraper.py
```

#### What It Does
1. **Determines current NFL week** by comparing today's date against the NFL schedule
2. **Scrapes team odds** including spreads, totals, and moneyline odds
3. **Collects player props** for passing, rushing, receiving, and touchdown statistics
4. **Organizes data by week** in dedicated folders with descriptive file names
5. **Handles API rate limiting** with automatic retry logic and usage tracking

### Configuration
- **API Key**: Set `ODDS_API_KEY` environment variable with your The Odds API key
- **Schedule File**: Uses `nfl2025sched.csv` to determine week boundaries
- **Bookmaker**: Focuses on DraftKings odds for consistency

### Data Files
- **Team Odds**: Contains game-level betting lines (spreads, totals, moneyline)
- **Player Props**: Individual player statistics with betting lines and odds
- **Weekly Organization**: Each week gets its own folder with clearly named files

## NFL Fun Stats Agent

The project now includes a fun stats agent (`stats_agent.py`) that generates focused, odds-aligned NFL statistics and insights for upcoming matchups.

### Features
- **Method-Based Architecture**: Clean, modular function-based design following .cursorrules principles
- **Odds-Aligned Analysis**: Integrates player props data to create actionable betting insights
- **High-Confidence Focus**: Generates only 10-20 high-confidence insights instead of hundreds
- **Player Performance Trends**: Analyzes recent performance patterns against betting lines
- **Team vs. Team Historical**: Examines historical matchup data between teams
- **Week-Aware Analysis**: Automatically determines current NFL week from 2025 schedule
- **CSV Output**: Human-readable insights saved to `data/fun_stats/` directory

### Key Improvements
- **Reduced Output Volume**: From 1,000+ insights to focused 10-20 high-quality insights
- **Stricter Filtering**: Only includes insights with 15%+ edge percentage or 75%+ hit rate
- **Higher Confidence**: Minimum 0.7 confidence threshold, prioritizes 0.8+ confidence
- **Deduplication**: Eliminates duplicate player/prop combinations
- **Betting Direction**: Clear OVER/UNDER recommendations based on historical data

### Usage
```bash
# Generate focused insights for current week (max 20)
python stats_agent.py

# Generate insights for specific week with custom limit
python -c "from stats_agent import run_stats_agent; run_stats_agent(week=1, max_insights=15)"
```

### Output Format
The agent generates a CSV file with columns:
- `week`, `game`, `team1`, `team2`: Game context
- `player`, `prop_type`, `betting_line`: Player and betting details
- `historical_avg`, `edge_percentage`, `hit_rate`: Statistical analysis
- `bet_direction`: OVER/UNDER/NEUTRAL recommendation
- `insight_text`: Human-readable summary
- `confidence`, `games_analyzed`: Quality metrics

### Example Insights
- **"Saquon Barkley averaging 167.0 rush yds vs 93.5 line in last 8 games"** (OVER)
- **"Dallas Goedert averaging 55.0 reception yds vs 38.5 line in last 8 games"** (OVER)
- **"CeeDee Lamb averaging 105.0 reception yds vs 72.5 line in last 8 games"** (OVER)

### Data Sources
- **Historical Game Data**: 2016-2024 seasons (68,000+ game records)
- **NFL Schedule**: 2025 season schedule for week determination
- **Player Statistics**: Individual performance data across all positions
- **Team Matchups**: Head-to-head historical data

### Configuration
Set the `GROK_API_KEY` environment variable to enable AI-powered insight enhancement:
```bash
export GROK_API_KEY="your_api_key_here"
```

## Responsible Scraping

To avoid overwhelming the host and to reduce the risk of being timed out or blocked, the scraper waits a random interval (between 1 and 3 seconds) between each web request. This is a best practice for ethical and responsible web scraping.

## Error Handling and Retry Logic

The scraper includes robust error handling for web requests:
- Each game data request is retried up to 3 times if it fails.
- Errors are logged to `scraper_errors.log`.
- If a page cannot be fetched after all retries, the script logs the failure and continues with the next game, ensuring the scraping process is resilient and does not stop on a single failure.
- When a page is successfully retrieved, a success message is printed.
- If a page fails after the maximum number of retries, the web driver is re-initialized and the request is retried once more.
- If it still fails after re-initialization, the program exits to prevent further issues.

## Testing

### Test the Scraper
To test the caching functionality:
1. Run the script first time - it will fetch fresh data from the website
2. Run the script again within 24 hours - it will use cached data
3. Check the `cache` directory to see the stored files

To test the data collection and CSV output:
1. Run the script:
   ```python
   python ben_scrape.py
   ```
2. After completion, check the `data/game_data_2024.csv` file for the collected player data.

### Test the Projection Engine
1. First, ensure you have game data:
   ```bash
   python ben_scrape.py
   ```
2. Then run the projection engine:
   ```bash
   # Basic projection engine
   python nfl_proj.py --game-data
   
   # With schedule and current week for next opponent determination
   python nfl_proj.py --game-data data/game_data_2024.csv nfl2025sched.csv 5
   ```
3. Check the output files:
   - `nfl24_team.csv` - Team statistics with opponents list and next opponents
   - `nfl24_players.csv` - Player statistics
   - `nfl23_proj.csv` - Final fantasy football projections

### Test the Bug Fix
To verify that the column naming issue has been resolved:

1. **Before the fix**: The program would fail with this error:
   ```
   KeyError: 'int'
   ```

2. **After the fix**: The program should run successfully and complete the projection calculations without errors.

3. **Test command**:
   ```bash
   python nfl_proj.py --game-data data/game_data_2024.csv nfl2025sched.csv 1
   ```

4. **Expected output**: The program should complete successfully and show:
   ```
   Projection Program Start with Game Data - [timestamp]:
   Loading game data from data/game_data_2024.csv...
   Loading schedule data from nfl2025sched.csv...
   Creating team dataset...
   Creating player dataset...
   Saved team and player datasets
   Projection Program End - [timestamp]
   ```

5. **Check for warnings**: The pandas FutureWarning about downcasting should no longer appear.

Example:
```python
python ben_scrape.py
python nfl_proj.py --game-data
```

The first run will show "Fetching fresh data from [URL]", while subsequent runs will show "Loading cached data for [URL]". 