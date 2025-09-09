# NFL Data Analysis & Betting Intelligence Platform

A comprehensive Python platform for NFL data collection, analysis, and betting intelligence. This system combines web scraping, statistical analysis, and AI-powered insights to generate actionable betting recommendations and fantasy football projections.

## 🏗️ Project Architecture

### Core Data Pipeline
```
Raw Data Collection → Processing & Analysis → AI-Powered Insights → Betting Recommendations
```

### Weekly Workflow
1. **Data Collection**: Scrape fresh NFL data and betting odds
2. **Processing**: Generate projections and statistical analysis
3. **Intelligence**: AI-powered betting recommendations and trend analysis
4. **Output**: Actionable insights for fantasy and betting decisions

## 📁 Project Files & Components

### Data Collection & Scraping
- **`nfl_data.py`** - **NEW**: Optimized NFL game data scraper with undetected Chrome driver
- **`pfr_scraper.py`** - Legacy NFL game data scraper from Pro Football Reference
- **`odds.py`** - Betting odds collection from The Odds API

### Analysis & Projections
- **`projection.py`** - Fantasy football projection engine with schedule strength normalization
- **`stats_agent.py`** - Historical trend analysis and statistical insights generator
- **`picks_agent.py`** - AI-powered betting recommendations with live search integration

### Data Management
- **`data/master_roster.xlsx`** - Current NFL active roster (player-team mappings)
- **`data/team_map.xlsx`** - Team name to abbreviation mappings
- **`data/player_name_mapping.csv`** - Odds names to projection names mappings
- **`nfl2025sched.csv`** - 2025 NFL season schedule

### Configuration & Utilities
- **`telegram_bot.py`** - Telegram bot integration for notifications
- **`prompt.txt`** - AI prompt templates for analysis
- **`.cursorrules`** - Development guidelines and coding standards

## 🚀 Weekly Data Pipeline

### Step 1: Collect Fresh NFL Data
```bash
# Scrape current season game data from Pro Football Reference (NEW OPTIMIZED VERSION)
python nfl_data.py 2025

# Or use legacy scraper
python pfr_scraper.py
```
**Output**: `data/game_data_2025.csv` - Complete player performance data

**New Features in nfl_data.py**:
- **Undetected Chrome Driver**: Bypasses Cloudflare protection
- **Method-Based Architecture**: Clean, modular, testable functions
- **Intelligent Caching**: 24-hour cache system for faster development
- **Retry Logic**: Robust error handling with automatic retries
- **Year Parameter**: Run with any year: `python nfl_data.py 2024`
- **Target Format Compliance**: Output matches exact CSV structure
- **Schedule-Based Scraping**: Efficient single-page approach vs team-by-team
- **Mathematical Snap Counts**: Calculated from pass attempts + rushes
- **Position Extraction**: Accurate player positions from snap count tables
- **Clean Weather Data**: Proper weather text extraction from game info
- **Team Assignment**: Correct player-to-team mapping

### Step 2: Generate Fantasy Projections
```bash
# Generate projections with active roster filtering
python nfl_proj.py --game-data data/game_data_2024.csv nfl2025sched.csv 1
```
**What it does**:
- Loads active roster from `data/master_roster.xlsx`
- Filters to active players only (eliminates injured/inactive noise)
- Creates team-level statistics with schedule strength normalization
- Generates fantasy football projections based on opponent matchups

**Output**: 
- `data/projections/nfl25_proj_week0.csv` - Fantasy projections
- `nfl25_team.csv` - Team statistics
- `nfl25_players.csv` - Player statistics

### Step 3: Collect Betting Odds
```bash
# Scrape current week's betting odds
python odds.py
```
**What it does**:
- Determines current NFL week from schedule
- Collects team odds (spreads, totals, moneyline)
- Gathers player props (passing, rushing, receiving stats)
- Organizes data by week in structured directories

**Output**: 
- `data/odds/week_01/team_odds_week_01.csv`
- `data/odds/week_01/player_props_week_01.csv`

### Step 4: AI-Powered Betting Analysis
```bash
# Generate AI-powered betting recommendations
python picks_agent.py
```
**What it does**:
- Compares projections to betting lines to find mathematical edges
- Uses live search to gather injury reports, news, and expert insights
- Sends top opportunities to Grok AI for intelligent analysis
- Returns top 10 betting recommendations with reasoning

**Output**: 
- `data/insights/grok_insights_week_01.json` - AI betting recommendations

### Step 5: Historical Trend Analysis
```bash
# Generate statistical insights and fun facts
python stats_agent.py
```
**What it does**:
- Analyzes 9 seasons of historical data (2016-2024)
- Compares player performance trends to current betting lines
- Identifies statistical anomalies and betting opportunities
- Generates ESPN-style insights using Grok AI

**Output**: 
- `data/nuggets/nuggets_week_01.json` - Raw statistical data
- `data/fun_stats/stats_insights_week_01.json` - AI-enhanced statistical insights

## 🔧 Setup & Configuration

### Prerequisites
```bash
# Install required packages
pip install pandas numpy selenium beautifulsoup4 requests xai-sdk openpyxl undetected-chromedriver
```

### Testing the New NFL Data Scraper
```bash
# Test basic functionality (recommended first)
python nfl_data.py test

# Scrape data for specific year
python nfl_data.py 2024

# Scrape current year (default)
python nfl_data.py
```

### API Keys
Create a `.env` file in the project root:
```bash
# .env file
GROK_API_KEY=your_grok_api_key_here
ODDS_API_KEY=your_odds_api_key_here
```

### Data Files
Ensure these files are present:
- `data/master_roster.xlsx` - Current NFL active roster
- `data/team_map.xlsx` - Team name mappings
- `nfl2025sched.csv` - 2025 NFL schedule

## 📊 Key Features

### Active Roster Filtering
- **Eliminates noise** from injured/inactive players
- **Cleans player names** (removes "(IR)", "(PUP)" suffixes)
- **Comprehensive logging** of filtering statistics
- **Data validation** to ensure projection accuracy

### Schedule Strength Normalization
- **Opponent analysis** - tracks all teams faced by each team
- **Strength of schedule** calculations for accurate projections
- **Next opponent determination** for matchup-based projections
- **League average comparisons** for normalized statistics

### AI-Powered Intelligence
- **Live search integration** for real-time news and injuries
- **Contextual analysis** combining projections, odds, and news
- **Confidence scoring** based on statistical variance
- **Risk assessment** for each betting recommendation

### Historical Analysis
- **9 seasons of data** (2016-2024) for trend analysis
- **Player-specific insights** based on career performance
- **Opponent matchup history** for predictive analysis
- **Statistical validation** with minimum sample sizes

## 🎯 Output Examples

### Fantasy Projections
```csv
name,proj_pass_att,proj_rush_att,proj_tar,proj_pass_yd,proj_rush_yd
Josh Allen,34.18,1.29,0.00,245.50,8.75
Saquon Barkley,0.00,9.66,3.31,0.00,67.25
```

### Betting Recommendations
```json
{
  "player": "Saquon Barkley",
  "prop": "Rushing Yards",
  "line": 93.5,
  "projection": 167.0,
  "edge": 78.6,
  "recommendation": "OVER",
  "confidence": "High",
  "reasoning": "Barkley averaging 167.0 rush yds vs 93.5 line in last 8 games"
}
```

### Statistical Insights
```csv
week,player,prop_type,betting_line,historical_avg,edge_percentage,bet_direction,confidence
1,Saquon Barkley,rush_yds,93.5,167.0,78.6,OVER,0.89
1,Dallas Goedert,rec_yds,38.5,55.0,42.9,OVER,0.82
```

## 🔍 Quality Assurance

### Data Validation
- **Active roster filtering** ensures only current players
- **Name matching** between odds and projections
- **Statistical thresholds** for meaningful insights
- **Error handling** for missing or invalid data

### Performance Metrics
- **Edge calculations** for mathematical advantage
- **Confidence scoring** based on standard deviations
- **Sample size requirements** for statistical significance
- **Hit rate tracking** for recommendation accuracy

## 📈 Monitoring & Maintenance

### Weekly Tasks
1. **Update active roster** in `data/master_roster.xlsx`
2. **Run complete pipeline** for current week
3. **Review AI recommendations** for accuracy
4. **Track performance** of betting suggestions

### Data Quality
- **Monitor name matching** between sources
- **Validate projection accuracy** against actual results
- **Update team mappings** as needed
- **Maintain API keys** and dependencies

## 🚨 Troubleshooting

### Common Issues
- **Missing API keys** - Check `.env` file configuration
- **Name mismatches** - Review player mapping files
- **Data validation errors** - Check active roster completeness
- **Projection failures** - Verify game data quality

### Log Files
- `scraper_errors.log` - Web scraping errors
- `odds_scraper.log` - Odds collection issues
- Console output - Real-time processing status

## 📚 Documentation

- **`CONTEXT.md`** - Project progress and current state
- **`.cursorrules`** - Development guidelines
- **Inline comments** - Detailed code documentation
- **Function docstrings** - API documentation

---

*This platform combines the power of data science, web scraping, and AI to provide the most comprehensive NFL analysis and betting intelligence available.*