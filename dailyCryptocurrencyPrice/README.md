The script uses the **CoinGecko public API** — no key needed. Here's a quick-start guide:

**Install the only dependency:**
```bash
pip install requests
```

**Run it:**
```bash
# Default: top 250 coins in USD, printed as a table
python crypto_crawler.py

# Fetch top 500 coins in EUR
python crypto_crawler.py --limit 500 --currency eur

# Search for a specific coin
python crypto_crawler.py --search solana

# Sort by 24h change
python crypto_crawler.py --sort change

# Save to CSV or JSON
python crypto_crawler.py --output coins.csv
python crypto_crawler.py --output coins.json --no-table
```

**What the output includes:**

| Field | Description |
|---|---|
| Rank | Market cap rank |
| Price | Current price with proper precision |
| 1h / 24h / 7d % | Price change over time windows |
| Market Cap | Total market capitalization |
| Volume (24h) | 24-hour trading volume |

The crawler handles rate limiting automatically — if CoinGecko throttles the request, it reads the `Retry-After` header and waits before retrying. Each page fetch is also spaced 1.2 seconds apart to stay within the free tier limits.
