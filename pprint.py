"""
Simple program to pretty print AI analysis from grok_insights and stats_insights files.

This program reads the JSON files and displays the analysis content with proper headers.
"""

import json
import sys
import os
from typing import Dict, Any


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


def print_grok_insights(data: Dict[str, Any]) -> None:
    """
    Print the GROK insights analysis with PICKS header.
    
    Args:
        data: Parsed JSON data from grok_insights file
    """
    print("=" * 80)
    print("PICKS")
    print("=" * 80)
    print()
    
    # Extract the analysis from ai_analysis.analysis
    if 'ai_analysis' in data and 'analysis' in data['ai_analysis']:
        analysis = data['ai_analysis']['analysis']
        # Print with proper text wrapping
        import textwrap
        wrapped_text = textwrap.fill(analysis, width=80, initial_indent="", subsequent_indent="")
        print(wrapped_text)
    else:
        print("No analysis found in ai_analysis.analysis")
    
    print()


def print_stats_insights(data: Dict[str, Any]) -> None:
    """
    Print the stats insights analysis with STATS header.
    
    Args:
        data: Parsed JSON data from stats_insights file
    """
    print("=" * 80)
    print("STATS")
    print("=" * 80)
    print()
    
    # Extract the insights from the insights array
    if 'insights' in data and data['insights']:
        # The insights are stored as a JSON string, so we need to parse it
        insights_str = data['insights'][0]
        try:
            insights_data = json.loads(insights_str)
            
            # Print each insight with proper formatting
            import textwrap
            for insight in insights_data:
                if isinstance(insight, dict) and 'insight' in insight:
                    insight_text = insight['insight']
                    wrapped_text = textwrap.fill(insight_text, width=78, initial_indent="• ", subsequent_indent="  ")
                    print(wrapped_text)
                    print()
                else:
                    wrapped_text = textwrap.fill(str(insight), width=78, initial_indent="• ", subsequent_indent="  ")
                    print(wrapped_text)
                    print()
        except json.JSONDecodeError:
            # If it's not JSON, print as text
            import textwrap
            wrapped_text = textwrap.fill(insights_str, width=80)
            print(wrapped_text)
    else:
        print("No insights found")
    
    print()


def main(week_number: int) -> None:
    """
    Main function to pretty print insights for a specific week.
    
    Args:
        week_number: NFL week number to display insights for
    """
    try:
        # Construct file paths
        grok_file = f"data/insights/grok_insights_week_{week_number:02d}.json"
        stats_file = f"data/fun_stats/stats_insights_week_{week_number:02d}.json"
        
        print(f"NFL Week {week_number} Analysis")
        print("=" * 80)
        print()
        
        # Load and print GROK insights
        try:
            grok_data = load_json_file(grok_file)
            print_grok_insights(grok_data)
        except FileNotFoundError:
            print(f"GROK insights file not found: {grok_file}")
            print()
        except json.JSONDecodeError as e:
            print(f"Error parsing GROK insights file: {e}")
            print()
        
        # Load and print stats insights
        try:
            stats_data = load_json_file(stats_file)
            print_stats_insights(stats_data)
        except FileNotFoundError:
            print(f"Stats insights file not found: {stats_file}")
            print()
        except json.JSONDecodeError as e:
            print(f"Error parsing stats insights file: {e}")
            print()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) != 2:
        print("Usage: python pretty_print_insights.py <week_number>")
        print("Example: python pretty_print_insights.py 2")
        sys.exit(1)
    
    try:
        week_number = int(sys.argv[1])
        main(week_number)
    except ValueError:
        print("Error: Week number must be an integer")
        print("Usage: python pretty_print_insights.py <week_number>")
        sys.exit(1)
