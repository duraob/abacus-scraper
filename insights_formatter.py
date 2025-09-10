"""
Enhanced NFL Insights Formatter

This program formats and displays AI analysis from grok_insights and stats_insights files
with improved readability and optional CSV export functionality.
"""

import json
import sys
import os
import csv
import re
from typing import Dict, Any, List, Tuple
from datetime import datetime


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_picks_from_analysis(analysis_text: str) -> List[Dict[str, str]]:
    """
    Extract individual picks from the analysis text.
    
    Args:
        analysis_text: The full analysis text from GROK
        
    Returns:
        List of dictionaries containing pick information
    """
    picks = []
    
    # Split by numbered sections (#### 1., #### 2., etc.)
    sections = re.split(r'#### \d+\.', analysis_text)
    
    for i, section in enumerate(sections[1:], 1):  # Skip first empty section
        pick_data = {
            'pick_number': i,
            'type': 'PICK',
            'player': '',
            'prop_type': '',
            'line': '',
            'recommendation': '',
            'confidence': '',
            'reasoning': '',
            'risk_factors': ''
        }
        
        # Extract player name (first line after the number)
        lines = section.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if '(' in first_line and ')' in first_line:
                pick_data['player'] = first_line.split('(')[0].strip()
        
        # Extract other fields using regex patterns
        prop_match = re.search(r'\*\*Prop Type and Line\*\*: (.+)', section)
        if prop_match:
            pick_data['prop_type'] = prop_match.group(1).strip()
        
        rec_match = re.search(r'\*\*Recommendation\*\*: (.+)', section)
        if rec_match:
            pick_data['recommendation'] = rec_match.group(1).strip()
        
        conf_match = re.search(r'\*\*Confidence Level\*\*: (.+)', section)
        if conf_match:
            pick_data['confidence'] = conf_match.group(1).strip()
        
        reason_match = re.search(r'\*\*Key Reasoning\*\*: (.+?)(?=\*\*Risk Factors\*\*|$)', section, re.DOTALL)
        if reason_match:
            pick_data['reasoning'] = reason_match.group(1).strip()
        
        risk_match = re.search(r'\*\*Risk Factors\*\*: (.+)', section, re.DOTALL)
        if risk_match:
            pick_data['risk_factors'] = risk_match.group(1).strip()
        
        picks.append(pick_data)
    
    return picks


def extract_stats_from_insights(insights_data: List[Dict]) -> List[Dict[str, str]]:
    """
    Extract individual stats insights from the insights data.
    
    Args:
        insights_data: List of insight dictionaries
        
    Returns:
        List of dictionaries containing stat information
    """
    stats = []
    
    for i, insight in enumerate(insights_data, 1):
        if isinstance(insight, dict) and 'insight' in insight:
            stat_data = {
                'pick_number': i,
                'type': 'STAT',
                'player': insight.get('player', ''),
                'prop_type': '',
                'line': '',
                'recommendation': '',
                'confidence': '',
                'reasoning': insight.get('insight', ''),
                'risk_factors': ''
            }
            stats.append(stat_data)
    
    return stats


def print_formatted_analysis(week_number: int, picks: List[Dict], stats: List[Dict]) -> None:
    """
    Print formatted analysis with proper spacing and readability.
    
    Args:
        week_number: NFL week number
        picks: List of pick dictionaries
        stats: List of stat dictionaries
    """
    import textwrap
    
    print("=" * 100)
    print(f"NFL WEEK {week_number} ANALYSIS")
    print("=" * 100)
    print()
    
    # Print PICKS section
    print("🎯 PICKS - AI Betting Recommendations")
    print("-" * 100)
    print()
    
    for pick in picks:
        print(f"#{pick['pick_number']}. {pick['player']}")
        print(f"   Prop: {pick['prop_type']}")
        print(f"   Recommendation: {pick['recommendation']} ({pick['confidence']} Confidence)")
        print()
        
        if pick['reasoning']:
            print(f"   💡 Reasoning:")
            # Use textwrap for proper formatting
            wrapped_reasoning = textwrap.fill(pick['reasoning'], width=90, initial_indent="      • ", subsequent_indent="        ")
            print(wrapped_reasoning)
            print()
        
        if pick['risk_factors']:
            print(f"   ⚠️  Risk Factors:")
            # Use textwrap for proper formatting
            wrapped_risks = textwrap.fill(pick['risk_factors'], width=90, initial_indent="      • ", subsequent_indent="        ")
            print(wrapped_risks)
            print()
        
        print("-" * 100)
        print()
    
    # Print STATS section
    print("📊 STATS - Historical Performance Insights")
    print("-" * 100)
    print()
    
    for stat in stats:
        if stat['player']:
            print(f"#{stat['pick_number']}. {stat['player']}")
        else:
            print(f"#{stat['pick_number']}. Historical Insight")
        
        if stat['reasoning']:
            # Use textwrap for proper formatting
            wrapped_insight = textwrap.fill(stat['reasoning'], width=90, initial_indent="   📈 ", subsequent_indent="       ")
            print(wrapped_insight)
        print()
    
    print("=" * 100)


def export_to_csv(week_number: int, picks: List[Dict], stats: List[Dict], output_file: str = None) -> str:
    """
    Export picks and stats to CSV file.
    
    Args:
        week_number: NFL week number
        picks: List of pick dictionaries
        stats: List of stat dictionaries
        output_file: Optional output file path
        
    Returns:
        Path to the created CSV file
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"nfl_week_{week_number}_analysis_{timestamp}.csv"
    
    # Combine picks and stats
    all_data = picks + stats
    
    # Define CSV headers
    headers = [
        'pick_number',
        'type',
        'player',
        'prop_type',
        'line',
        'recommendation',
        'confidence',
        'reasoning',
        'risk_factors'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for row in all_data:
            # Clean up the data for CSV
            clean_row = {}
            for header in headers:
                value = row.get(header, '')
                # Remove newlines and extra whitespace for CSV
                if isinstance(value, str):
                    value = re.sub(r'\s+', ' ', value.strip())
                clean_row[header] = value
            writer.writerow(clean_row)
    
    return output_file


def main(week_number: int, export_csv: bool = False) -> None:
    """
    Main function to format and display insights for a specific week.
    
    Args:
        week_number: NFL week number to display insights for
        export_csv: Whether to export to CSV file
    """
    try:
        # Construct file paths
        grok_file = f"data/insights/grok_insights_week_{week_number:02d}.json"
        stats_file = f"data/fun_stats/stats_insights_week_{week_number:02d}.json"
        
        picks = []
        stats = []
        
        # Load and process GROK insights
        try:
            grok_data = load_json_file(grok_file)
            if 'ai_analysis' in grok_data and 'analysis' in grok_data['ai_analysis']:
                analysis_text = grok_data['ai_analysis']['analysis']
                picks = extract_picks_from_analysis(analysis_text)
                print(f"✅ Loaded {len(picks)} picks from GROK analysis")
            else:
                print(f"⚠️  No analysis found in {grok_file}")
        except FileNotFoundError:
            print(f"⚠️  GROK insights file not found: {grok_file}")
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing GROK insights file: {e}")
        
        # Load and process stats insights
        try:
            stats_data = load_json_file(stats_file)
            if 'insights' in stats_data and stats_data['insights']:
                insights_list = stats_data['insights']
                
                # Check if insights is a list of dictionaries (new format) or a JSON string (old format)
                if isinstance(insights_list, list) and len(insights_list) > 0:
                    if isinstance(insights_list[0], dict):
                        # New format: list of dictionaries
                        stats = extract_stats_from_insights(insights_list)
                        print(f"✅ Loaded {len(stats)} stats from insights (new format)")
                    else:
                        # Old format: list containing JSON string
                        insights_str = insights_list[0]
                        try:
                            # Try to parse the JSON string
                            parsed_insights = json.loads(insights_str)
                            stats = extract_stats_from_insights(parsed_insights)
                            print(f"✅ Loaded {len(stats)} stats from insights (old format)")
                        except json.JSONDecodeError:
                            # If it's not valid JSON, try to extract insights manually
                            print(f"⚠️  Could not parse insights JSON, trying manual extraction...")
                            # Look for insight patterns in the text
                            insight_pattern = r'"insight":\s*"([^"]+)"'
                            matches = re.findall(insight_pattern, insights_str)
                            stats = []
                            for i, match in enumerate(matches, 1):
                                stat_data = {
                                    'pick_number': i,
                                    'type': 'STAT',
                                    'player': '',
                                    'prop_type': '',
                                    'line': '',
                                    'recommendation': '',
                                    'confidence': '',
                                    'reasoning': match,
                                    'risk_factors': ''
                                }
                                stats.append(stat_data)
                            print(f"✅ Loaded {len(stats)} stats from manual extraction")
                else:
                    print(f"⚠️  No insights found in {stats_file}")
            else:
                print(f"⚠️  No insights found in {stats_file}")
        except FileNotFoundError:
            print(f"⚠️  Stats insights file not found: {stats_file}")
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing stats insights file: {e}")
        
        # Print formatted analysis
        if picks or stats:
            print_formatted_analysis(week_number, picks, stats)
            
            # Export to CSV if requested
            if export_csv:
                csv_file = export_to_csv(week_number, picks, stats)
                print(f"📊 Exported to CSV: {csv_file}")
        else:
            print("❌ No data found to display")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python insights_formatter.py <week_number> [--csv]")
        print("Example: python insights_formatter.py 2")
        print("Example: python insights_formatter.py 2 --csv")
        sys.exit(1)
    
    try:
        week_number = int(sys.argv[1])
        export_csv = '--csv' in sys.argv
        
        main(week_number, export_csv)
    except ValueError:
        print("❌ Error: Week number must be an integer")
        print("Usage: python insights_formatter.py <week_number> [--csv]")
        sys.exit(1)
