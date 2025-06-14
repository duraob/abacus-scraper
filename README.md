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

## Testing

To test the caching functionality:
1. Run the script first time - it will fetch fresh data from the website
2. Run the script again within 24 hours - it will use cached data
3. Check the `cache` directory to see the stored files

Example:
```python
python ben_scrape.py
```

The first run will show "Fetching fresh data from [URL]", while subsequent runs will show "Loading cached data for [URL]". 