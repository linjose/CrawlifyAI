"""
main.py - Entry point for the commodity price scraper.

Usage examples
--------------
# Fetch all default commodities once
python main.py

# Fetch specific commodities only
python main.py --commodities "Gold" "Natural Gas"

# Run as a daily scheduler (blocks forever, runs at 18:00 UTC)
python main.py --schedule --schedule-time 18:00

# Dry-run: fetch prices but do NOT write to the database
python main.py --dry-run

# Show the latest prices stored in the database
python main.py --show-latest
"""

import argparse
import sys
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv

from src.crawler import DEFAULT_COMMODITIES, CommodityScraper
from src.db import DatabaseManager
from src.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


# ── Core scrape-and-store job ─────────────────────────────────────────────────

def run_job(
    commodities: dict[str, str],
    db: DatabaseManager,
    dry_run: bool = False,
) -> None:
    """
    Fetch the latest commodity prices and persist them to PostgreSQL.

    Parameters
    ----------
    commodities:
        Mapping of name → ticker to scrape.
    db:
        Open DatabaseManager instance.
    dry_run:
        If True, print results but skip database writes.
    """
    logger.info("=" * 60)
    logger.info("Scrape job started at %s", datetime.utcnow().isoformat())
    logger.info("Commodities: %s", list(commodities.keys()))

    scraper = CommodityScraper(commodities=commodities)
    prices  = scraper.fetch_all()

    if not prices:
        logger.warning("No prices retrieved — nothing to persist.")
        return

    logger.info("Retrieved %d price(s):", len(prices))
    for cp in prices:
        logger.info("  %-25s %10.4f %s  (%s)", cp.commodity_name, cp.price, cp.currency, cp.price_date)

    if dry_run:
        logger.info("[DRY RUN] Skipping database write.")
    else:
        inserted, skipped = db.upsert_prices(prices)
        logger.info("Persisted: %d new row(s), %d skipped.", inserted, skipped)

    logger.info("Job finished at %s", datetime.utcnow().isoformat())
    logger.info("=" * 60)


# ── CLI helpers ───────────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="commodity-scraper",
        description="Fetch daily commodity prices and store them in PostgreSQL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--commodities",
        nargs="+",
        metavar="NAME",
        help=(
            "One or more commodity names to fetch (must match keys in DEFAULT_COMMODITIES). "
            "Example: --commodities Gold \"Natural Gas\". "
            f"Available: {', '.join(DEFAULT_COMMODITIES.keys())}"
        ),
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run as a daily scheduler instead of executing once.",
    )
    parser.add_argument(
        "--schedule-time",
        default="18:00",
        metavar="HH:MM",
        help="UTC time to run the daily job (default: 18:00).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch prices but do NOT write to the database.",
    )
    parser.add_argument(
        "--show-latest",
        action="store_true",
        help="Print the most recent stored price for each commodity and exit.",
    )

    return parser


def resolve_commodities(names: list[str] | None) -> dict[str, str]:
    """
    Map CLI names back to the DEFAULT_COMMODITIES ticker dict.

    Exits with an error message if any name is not found.
    """
    if not names:
        return DEFAULT_COMMODITIES

    resolved = {}
    for name in names:
        if name not in DEFAULT_COMMODITIES:
            logger.error(
                "Unknown commodity %r. Available: %s",
                name, ", ".join(DEFAULT_COMMODITIES.keys()),
            )
            sys.exit(1)
        resolved[name] = DEFAULT_COMMODITIES[name]
    return resolved


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_arg_parser()
    args   = parser.parse_args()

    commodities = resolve_commodities(args.commodities)

    # Initialise DB (creates table if not exists)
    db = DatabaseManager()
    if not args.dry_run:
        db.init_db()

    try:
        # ── Show latest and exit ─────────────────────────────────────
        if args.show_latest:
            rows = db.get_latest_prices()
            if not rows:
                print("No data found in the database.")
            else:
                print(f"\n{'Commodity':<26} {'Ticker':<10} {'Price':>12} {'Ccy':<6} {'Date'}")
                print("-" * 65)
                for r in rows:
                    print(
                        f"{r['commodity_name']:<26} "
                        f"{r['ticker']:<10} "
                        f"{float(r['price']):>12.4f} "
                        f"{r['currency']:<6} "
                        f"{r['price_date']}"
                    )
                print()
            return

        # ── Scheduled mode ───────────────────────────────────────────
        if args.schedule:
            logger.info(
                "Scheduler started. Job will run daily at %s UTC.",
                args.schedule_time,
            )
            schedule.every().day.at(args.schedule_time).do(
                run_job, commodities=commodities, db=db, dry_run=args.dry_run
            )
            # Run immediately on startup so you don't wait until tomorrow
            run_job(commodities=commodities, db=db, dry_run=args.dry_run)

            while True:
                schedule.run_pending()
                time.sleep(30)

        # ── Single-shot mode ─────────────────────────────────────────
        else:
            run_job(commodities=commodities, db=db, dry_run=args.dry_run)

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
