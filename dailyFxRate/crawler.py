"""
Daily FX Rate Crawler
Source: https://data.gov.tw/dataset/11339
CSV URL: https://www.taifex.com.tw/data_gov/taifex_open_data.asp?data_name=DailyForeignExchangeRates

Downloads the CSV and upserts all rows into PostgreSQL.
"""

import os
import io
import logging
import requests
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fx_crawler.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

CSV_URL = (
    "https://www.taifex.com.tw/data_gov/taifex_open_data.asp"
    "?data_name=DailyForeignExchangeRates"
)

DB_CONFIG = {
    "host":     os.getenv("PG_HOST", "localhost"),
    "port":     int(os.getenv("PG_PORT", 5432)),
    "dbname":   os.getenv("PG_DB",   "fx_rates"),
    "user":     os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASSWORD", ""),
}

TABLE = "daily_fx_rates"

# Map CSV column names → PostgreSQL column names
COLUMN_MAP = {
    "日期":           "date",
    "美元_新台幣(匯率)":  "usd_twd",
    "人民幣_新台幣(匯率)": "cny_twd",
    "歐元_美元(匯率)":   "eur_usd",
    "美元_日幣(匯率)":   "usd_jpy",
    "英鎊_美元(匯率)":   "gbp_usd",
    "澳幣_美元(匯率)":   "aud_usd",
    "美元_港幣(匯率)":   "usd_hkd",
    "美元_人民幣(匯率)":  "usd_cny",
    "美元_南非幣(匯率)":  "usd_zar",
    "紐幣_美元(匯率)":   "nzd_usd",
}

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    date       DATE         PRIMARY KEY,
    usd_twd    NUMERIC(12, 4),
    cny_twd    NUMERIC(12, 4),
    eur_usd    NUMERIC(12, 4),
    usd_jpy    NUMERIC(12, 4),
    gbp_usd    NUMERIC(12, 4),
    aud_usd    NUMERIC(12, 4),
    usd_hkd    NUMERIC(12, 4),
    usd_cny    NUMERIC(12, 4),
    usd_zar    NUMERIC(12, 4),
    nzd_usd    NUMERIC(12, 4),
    imported_at TIMESTAMPTZ DEFAULT NOW()
);
"""

# ── Download ─────────────────────────────────────────────────────────────────

def download_csv() -> pd.DataFrame:
    """Download the CSV and return a cleaned DataFrame."""
    log.info("Downloading CSV from %s", CSV_URL)
    resp = requests.get(CSV_URL, timeout=30)
    resp.raise_for_status()

    # The file is Big5 / UTF-8 — try both
    for enc in ("utf-8-sig", "big5", "cp950"):
        try:
            df = pd.read_csv(io.StringIO(resp.content.decode(enc)))
            log.info("Decoded with %s — %d rows", enc, len(df))
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    else:
        raise ValueError("Could not decode CSV with any known encoding")

    # Strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]

    # Keep only known columns
    known = [c for c in COLUMN_MAP if c in df.columns]
    df = df[known].copy()
    df.rename(columns=COLUMN_MAP, inplace=True)

    # Parse date — format is usually YYYY/MM/DD or YYYY-MM-DD
    df["date"] = pd.to_datetime(df["date"].astype(str).str.strip(), errors="coerce")
    df.dropna(subset=["date"], inplace=True)
    df["date"] = df["date"].dt.date

    # Numeric columns
    rate_cols = [c for c in df.columns if c != "date"]
    for col in rate_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.drop_duplicates(subset=["date"], keep="last", inplace=True)
    df.sort_values("date", inplace=True)
    log.info("Parsed %d unique date rows", len(df))
    return df

# ── Database ──────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    log.info("Table '%s' is ready", TABLE)

def upsert(conn, df: pd.DataFrame):
    """Insert or update all rows — primary key is date."""
    rate_cols = [c for c in df.columns if c != "date"]
    all_cols  = ["date"] + rate_cols

    rows = [
        tuple(row[c] if pd.notna(row[c]) else None for c in all_cols)
        for _, row in df.iterrows()
    ]

    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in rate_cols)
    sql = f"""
        INSERT INTO {TABLE} ({", ".join(all_cols)})
        VALUES %s
        ON CONFLICT (date) DO UPDATE SET {set_clause},
            imported_at = NOW()
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()
    log.info("Upserted %d rows into '%s'", len(rows), TABLE)

# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    start = datetime.now()
    log.info("=== FX crawler started at %s ===", start.isoformat())

    try:
        df = download_csv()
    except Exception as exc:
        log.error("Download failed: %s", exc)
        raise

    try:
        conn = get_connection()
        ensure_table(conn)
        upsert(conn, df)
        conn.close()
    except Exception as exc:
        log.error("Database error: %s", exc)
        raise

    elapsed = (datetime.now() - start).total_seconds()
    log.info("=== Done in %.1f seconds ===", elapsed)

if __name__ == "__main__":
    run()
