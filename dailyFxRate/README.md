CSV download URL: `https://www.taifex.com.tw/data_gov/taifex_open_data.asp?data_name=DailyForeignExchangeRates`.

**Quick setup:**
```bash
pip install -r requirements.txt
cp .env.example .env        # fill in your PostgreSQL credentials
python crawler.py           # run once to test & seed the DB
```

**For daily automation, pick one:**
- `python scheduler.py` — long-running process with APScheduler, fires every weekday at 18:00 Taiwan time (+ immediately on startup). Good for servers with systemd.
- **crontab** — simpler, add one line to `crontab -e`. The README has the exact line for both UTC+8 and UTC servers.

**What `crawler.py` does:**
1. Downloads the CSV directly from TAIFEX (`taifex.com.tw`) — the actual data source linked from data.gov.tw
2. Handles Big5/UTF-8 encoding automatically (the site uses Traditional Chinese headers)
3. Parses all 10 exchange rate columns and the date
4. Upserts into PostgreSQL via `ON CONFLICT (date) DO UPDATE` — safe to re-run, no duplicates

**The table** is auto-created on first run with `date` as the primary key and `NUMERIC(12,4)` for all rate columns.
