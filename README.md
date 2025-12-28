# Stock Finder

A command-line tool for scanning stocks to find high-momentum gainers, inspired by Jeffrey Neumann's trading approach from "Unknown Market Wizards".

## What It Does

Scans a universe of stocks to identify those with significant price gains (e.g., 500%+) over a configurable lookback period. This helps filter down thousands of stocks to a focused watchlist for further research.

## Installation

```bash
# Clone the repository
cd stock-finder

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt
```

## Usage

### Check a Single Stock

```bash
# Check HIMS for gains over 3 years
python -m stock_finder check HIMS --years 3

# Output:
# Max gain found:
#   Gain: 1,089.3%
#   Low:  $5.78 on 2023-10-27
#   High: $68.74 on 2025-02-19
#   Current: $34.31
#   Days to peak: 327
```

### Scan Multiple Stocks

```bash
# Scan specific tickers for 500%+ gainers
python -m stock_finder scan --tickers "HIMS,RKLB,PL,SMCI,NVDA,AAPL" --min-gain 500

# Scan from a CSV file
python -m stock_finder scan --universe data/tickers/my_watchlist.csv --min-gain 300

# Output as JSON
python -m stock_finder scan --tickers "HIMS,RKLB" --output json

# Save results to file
python -m stock_finder scan --tickers "HIMS,RKLB" --save
```

### Command Options

```
scan command:
  --min-gain FLOAT    Minimum gain percentage (default: 500)
  --years INT         Years to look back (default: 3)
  --universe PATH     CSV file with ticker list
  --tickers TEXT      Comma-separated list of tickers
  --output FORMAT     Output format: table, csv, json (default: table)
  --save              Save results to file
  --save-dir PATH     Directory to save results

check command:
  TICKER              Stock ticker to check
  --years INT         Years to look back (default: 3)

Global options:
  -v, --verbose       Enable verbose logging
  --config PATH       Path to config file
```

## Configuration

Edit `config/settings.yaml` to customize defaults:

```yaml
scan:
  min_gain_pct: 500
  lookback_years: 3

data:
  rate_limit_delay: 0.1  # Seconds between API calls

output:
  default_format: "table"
  save_dir: "output"
```

## Project Structure

```
stock-finder/
├── src/stock_finder/
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── data/               # Data fetching layer
│   │   ├── base.py         # Abstract provider interface
│   │   ├── yfinance_provider.py
│   │   └── ticker_source.py
│   ├── scanners/           # Scanning strategies
│   │   └── gainer_scanner.py
│   ├── models/             # Data models
│   │   └── results.py
│   └── output/             # Output formatters
│       └── formatters.py
├── tests/
│   ├── unit/               # Fast tests (no network)
│   └── integration/        # Tests with real API calls
├── config/
│   └── settings.yaml
└── data/tickers/           # Ticker lists
```

## Running Tests

```bash
# All tests
pytest

# Unit tests only (fast, no network)
pytest tests/unit

# Integration tests (requires network)
pytest tests/integration -m integration

# With coverage
pytest --cov=stock_finder
```

## Extending

### Add a New Data Provider

```python
from stock_finder.data.base import DataProvider

class MyProvider(DataProvider):
    def get_historical(self, ticker, start, end):
        # Fetch from your data source
        pass

    def get_current_price(self, ticker):
        pass
```

### Add a New Scanner

```python
from stock_finder.scanners.base import Scanner

class MyScanner(Scanner):
    def scan(self, tickers):
        # Your scanning logic
        pass

    def scan_single(self, ticker):
        pass
```

## Notes

- Data is fetched from Yahoo Finance (yfinance library)
- No API key required
- Rate limiting is applied to avoid being blocked
- For production use with large ticker lists, consider a paid data provider
