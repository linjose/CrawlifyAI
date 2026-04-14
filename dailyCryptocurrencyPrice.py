"""
Cryptocurrency Price Crawler
Fetches live prices for all top cryptocurrencies using the CoinGecko public API.
No API key required.

Usage:
    python crypto_crawler.py                        # Top 250 coins, USD, table view
    python crypto_crawler.py --limit 500            # Top 500 coins
    python crypto_crawler.py --currency eur         # Prices in EUR
    python crypto_crawler.py --search bitcoin       # Filter by name/symbol
    python crypto_crawler.py --sort change          # Sort by 24h change
    python crypto_crawler.py --output coins.csv     # Save to CSV
    python crypto_crawler.py --output coins.json    # Save to JSON

Requirements:
    pip install requests
"""

import requests
import time
import json
import csv
import argparse
import sys
from datetime import datetime


BASE_URL = "https://api.coingecko.com/api/v3"
PER_PAGE = 250  # Max allowed by CoinGecko per request


CURRENCY_SYMBOLS = {
    "usd": "$", "eur": "€", "gbp": "£", "jpy": "¥",
    "twd": "NT$", "aud": "A$", "cad": "C$", "chf": "CHF",
    "cny": "¥", "krw": "₩", "btc": "₿", "eth": "Ξ",
}


def fetch_page(page: int, currency: str, retries: int = 3) -> list[dict]:
    """Fetch a single page of coin market data."""
    url = f"{BASE_URL}/coins/markets"
    params = {
        "vs_currency": currency,
        "order": "market_cap_desc",
        "per_page": PER_PAGE,
        "page": page,
        "sparkline": False,
        "price_change_percentage": "1h,24h,7d",
    }

    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"  Rate limited. Waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt < retries - 1:
                print(f"  Request failed ({e}). Retrying in 5s...")
                time.sleep(5)
            else:
                raise

    return []


def fetch_all_coins(limit: int, currency: str) -> list[dict]:
    """Fetch up to `limit` coins across multiple pages."""
    coins = []
    pages_needed = (limit + PER_PAGE - 1) // PER_PAGE
    print(f"\nFetching top {limit} coins in {currency.upper()}...")

    for page in range(1, pages_needed + 1):
        print(f"  Page {page}/{pages_needed}...", end=" ", flush=True)
        data = fetch_page(page, currency)
        coins.extend(data)
        print(f"{len(data)} coins retrieved.")
        if len(data) < PER_PAGE:
            break  # Last page returned fewer results — we're done
        if page < pages_needed:
            time.sleep(1.2)  # Respect rate limits between pages

    return coins[:limit]


def format_price(value, currency: str) -> str:
    """Format a price value with the appropriate symbol and precision."""
    if value is None:
        return "N/A"
    sym = CURRENCY_SYMBOLS.get(currency, currency.upper() + " ")
    if currency in ("btc", "eth"):
        return f"{sym}{value:.8f}"
    if value >= 1_000_000:
        return f"{sym}{value:,.0f}"
    if value >= 1_000:
        return f"{sym}{value:,.2f}"
    if value >= 1:
        return f"{sym}{value:.4f}"
    return f"{sym}{value:.8f}"


def format_mcap(value, currency: str) -> str:
    """Format market cap in human-readable form."""
    if value is None:
        return "N/A"
    sym = CURRENCY_SYMBOLS.get(currency, "$")
    if value >= 1e12:
        return f"{sym}{value/1e12:.2f}T"
    if value >= 1e9:
        return f"{sym}{value/1e9:.2f}B"
    if value >= 1e6:
        return f"{sym}{value/1e6:.2f}M"
    return f"{sym}{value:,.0f}"


def format_change(value) -> str:
    """Format a percentage change with sign and colour escape codes."""
    if value is None:
        return "  N/A  "
    sign = "+" if value >= 0 else ""
    color = "\033[92m" if value >= 0 else "\033[91m"  # green / red
    reset = "\033[0m"
    return f"{color}{sign}{value:.2f}%{reset}"


def apply_filters(coins: list[dict], search: str, sort: str) -> list[dict]:
    """Filter by search term and sort by selected field."""
    if search:
        q = search.lower()
        coins = [c for c in coins if q in c["name"].lower() or q in c["symbol"].lower()]

    sort_keys = {
        "market_cap": lambda c: c.get("market_cap") or 0,
        "price":      lambda c: c.get("current_price") or 0,
        "change":     lambda c: c.get("price_change_percentage_24h") or 0,
        "volume":     lambda c: c.get("total_volume") or 0,
        "name":       lambda c: c.get("name", "").lower(),
    }
    reverse = sort != "name"
    coins.sort(key=sort_keys.get(sort, sort_keys["market_cap"]), reverse=reverse)
    return coins


def print_table(coins: list[dict], currency: str) -> None:
    """Print a formatted table to stdout."""
    col_widths = [5, 22, 8, 14, 10, 10, 10, 14, 14]
    headers = ["Rank", "Name", "Symbol", "Price", "1h %", "24h %", "7d %", "Market Cap", "Volume (24h)"]

    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_row = "|" + "|".join(f" {h:<{w}} " for h, w in zip(headers, col_widths)) + "|"

    print("\n" + sep)
    print(header_row)
    print(sep)

    for c in coins:
        rank      = str(c.get("market_cap_rank") or "—")
        name      = (c["name"][:20] + "…") if len(c["name"]) > 20 else c["name"]
        symbol    = c["symbol"].upper()
        price     = format_price(c.get("current_price"), currency)
        chg1h     = f"{c.get('price_change_percentage_1h_in_currency', 0) or 0:+.2f}%"
        chg24h    = f"{c.get('price_change_percentage_24h', 0) or 0:+.2f}%"
        chg7d     = f"{c.get('price_change_percentage_7d_in_currency', 0) or 0:+.2f}%"
        mcap      = format_mcap(c.get("market_cap"), currency)
        volume    = format_mcap(c.get("total_volume"), currency)

        row = "|" + "|".join(
            f" {v:<{w}} " for v, w in zip(
                [rank, name, symbol, price, chg1h, chg24h, chg7d, mcap, volume],
                col_widths
            )
        ) + "|"
        print(row)

    print(sep)
    print(f"\nTotal: {len(coins)} coins  |  Currency: {currency.upper()}  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def save_csv(coins: list[dict], path: str, currency: str) -> None:
    """Write results to a CSV file."""
    fields = [
        "market_cap_rank", "id", "symbol", "name", "current_price",
        "market_cap", "total_volume",
        "price_change_percentage_1h_in_currency",
        "price_change_percentage_24h",
        "price_change_percentage_7d_in_currency",
        "circulating_supply", "total_supply", "max_supply",
        "ath", "ath_date", "atl", "atl_date", "last_updated",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(coins)
    print(f"\nSaved {len(coins)} coins to {path}")


def save_json(coins: list[dict], path: str) -> None:
    """Write results to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(coins, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(coins)} coins to {path}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Crypto price crawler — fetches live prices from CoinGecko."
    )
    parser.add_argument("--limit",    type=int,   default=250,     help="Number of coins to fetch (default: 250)")
    parser.add_argument("--currency", type=str,   default="usd",   help="Quote currency, e.g. usd, eur, gbp (default: usd)")
    parser.add_argument("--search",   type=str,   default="",      help="Filter coins by name or symbol")
    parser.add_argument("--sort",     type=str,   default="market_cap",
                        choices=["market_cap", "price", "change", "volume", "name"],
                        help="Sort field (default: market_cap)")
    parser.add_argument("--output",   type=str,   default="",      help="Optional output file path (.csv or .json)")
    parser.add_argument("--no-table", action="store_true",         help="Suppress table output (useful with --output)")
    return parser.parse_args()


def main():
    args = parse_args()
    currency = args.currency.lower()

    try:
        coins = fetch_all_coins(args.limit, currency)
    except Exception as e:
        print(f"\nError fetching data: {e}")
        sys.exit(1)

    if not coins:
        print("No data returned. Check your connection or try again later.")
        sys.exit(1)

    coins = apply_filters(coins, args.search, args.sort)

    if not args.no_table:
        print_table(coins, currency)

    if args.output:
        ext = args.output.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            save_csv(coins, args.output, currency)
        elif ext == "json":
            save_json(coins, args.output)
        else:
            print(f"Unknown extension '.{ext}'. Use .csv or .json")


if __name__ == "__main__":
    main()
