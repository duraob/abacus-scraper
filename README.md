# PFR Scraper

A Python-based web scraper for Pro Football Reference data.

## Features

- Web scraping using Selenium and BeautifulSoup4
- Local caching system to reduce website requests during testing
- Modular and reusable functions for common scraping tasks

## Caching System

The scraper includes a file-based caching system that:
- Stores scraped data in a `cache` directory
- Uses MD5 hashes of URLs as unique cache file names
- Automatically expires cache after 24 hours
- Falls back to live web requests if cache is missing or expired

## Data Collection Efficiency

Player data is now collected using a list of dictionaries and converted to a DataFrame at the end of scraping. This approach is more efficient and avoids the deprecated `pandas.DataFrame.append` method.

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

Example:
```python
python ben_scrape.py
```

The first run will show "Fetching fresh data from [URL]", while subsequent runs will show "Loading cached data for [URL]". 