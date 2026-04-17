# 📈 Commodity Price Scraper

A production-ready Python scraper that collects daily commodity prices from
**Yahoo Finance** and persists them to **PostgreSQL**.

---

## Project Structure

```
commodity_scraper/
├── main.py                  # CLI entry point & scheduler
├── src/
│   ├── __init__.py
│   ├── crawler.py           # Yahoo Finance scraper (yfinance)
│   ├── db.py                # SQLAlchemy ORM + PostgreSQL persistence
│   └── logger.py            # Colorized logging (file + console)
├── sql/
│   └── init.sql             # Manual DB init / DBA reference
├── logs/                    # Auto-created at runtime
├── .env.example             # Environment variable template
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Data Source

| Layer | Details |
|-------|---------|
| Library | [`yfinance`](https://github.com/ranaroussi/yfinance) |
| Upstream | Yahoo Finance public JSON endpoints |
| Auth required | No API key needed |
| Method | HTTP GET via `requests` (wrapped by yfinance) |
| Data | Adjusted daily OHLCV for futures contracts |

### Commodity Tickers

| Name | Ticker | Exchange |
|------|--------|----------|
| Crude Oil (WTI) | `CL=F` | NYMEX |
| Brent Crude | `BZ=F` | ICE |
| Gold | `GC=F` | COMEX |
| Silver | `SI=F` | COMEX |
| Natural Gas | `NG=F` | NYMEX |
| Copper | `HG=F` | COMEX |
| Wheat | `ZW=F` | CBOT |
| Corn | `ZC=F` | CBOT |

All are **front-month continuous futures contracts**.

---

## Quick Start

### 1. Clone & configure

```bash
git clone <repo-url>
cd commodity_scraper

cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up PostgreSQL

```bash
# Option A — use the provided docker-compose
docker compose up -d postgres

# Option B — manual (already have PostgreSQL)
psql -U postgres -c "CREATE DATABASE commodities_db;"
psql -U postgres -d commodities_db -f sql/init.sql
```

### 4. Run the scraper

```bash
# Fetch all commodities once
python main.py

# Fetch specific commodities
python main.py --commodities Gold "Natural Gas" Silver

# Dry-run (no DB writes)
python main.py --dry-run

# Show latest prices in the database
python main.py --show-latest

# Run as a daily scheduler (blocks; runs at 18:00 UTC every day)
python main.py --schedule --schedule-time 18:00
```

---

## Docker (all-in-one)

```bash
# Copy and edit your .env first
cp .env.example .env

# Build and start everything (PostgreSQL + daily scraper)
docker compose up -d

# One-shot run
docker compose run --rm scraper

# Fetch specific commodities
docker compose run --rm scraper --commodities Gold "Crude Oil (WTI)"

# Tail logs
docker compose logs -f scraper
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `commodities_db` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | *(empty)* | Database password |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout (s) |
| `MAX_RETRIES` | `3` | Fetch retry attempts |
| `RETRY_DELAY` | `5` | Base retry delay (s) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FILE` | `logs/scraper.log` | Log file path |

---

## Database Schema

```sql
CREATE TABLE commodity_prices (
    id             SERIAL          PRIMARY KEY,
    commodity_name VARCHAR(120)    NOT NULL,
    ticker         VARCHAR(20)     NOT NULL,
    price          NUMERIC(18, 6)  NOT NULL,
    currency       VARCHAR(10)     NOT NULL DEFAULT 'USD',
    price_date     DATE            NOT NULL,
    fetched_at     TIMESTAMP       NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_commodity_price_date UNIQUE (commodity_name, price_date)
);
```

Duplicate rows (same commodity + same date) are silently ignored via
`INSERT … ON CONFLICT DO NOTHING`.

---

## Cron Job Alternative

If you prefer cron over the built-in `--schedule` flag:

```cron
# /etc/cron.d/commodity-scraper
# Run at 18:05 UTC every weekday
5 18 * * 1-5  scraper_user  cd /opt/commodity_scraper && \
    /opt/commodity_scraper/.venv/bin/python main.py >> /var/log/commodity_scraper.log 2>&1
```

---

## Retry Logic

Each ticker fetch uses **`tenacity`** with exponential back-off:

- Up to `MAX_RETRIES` attempts (default 3)
- Wait: 5 s → 10 s → 20 s … (capped at 60 s)
- Failed tickers are logged as `ERROR` and skipped; the rest continue

---

## Testing

```bash
# Quick sanity check (no DB required)
python main.py --dry-run --commodities Gold "Natural Gas"
```

Expected output:
```
2024-01-15 18:00:01 [INFO    ] src.crawler - ✓ GC=F  Gold  2052.1000 USD
2024-01-15 18:00:02 [INFO    ] src.crawler - ✓ NG=F  Natural Gas  2.6450 USD
2024-01-15 18:00:02 [INFO    ] __main__   - [DRY RUN] Skipping database write.
```
