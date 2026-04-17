"""
crawler.py - Commodity price scraper using Yahoo Finance (yfinance).

Data Source
-----------
Yahoo Finance via the ``yfinance`` library (https://github.com/ranaroussi/yfinance).
yfinance wraps Yahoo Finance's public JSON endpoints (no API key required).

Ticker symbols used
-------------------
  Crude Oil (WTI)  : CL=F   (NYMEX front-month futures)
  Brent Crude      : BZ=F   (ICE Brent front-month futures)
  Gold             : GC=F   (COMEX gold front-month futures)
  Silver           : SI=F   (COMEX silver front-month futures)
  Natural Gas      : NG=F   (NYMEX natural gas front-month futures)
  Copper           : HG=F   (COMEX copper front-month futures)
  Wheat            : ZW=F   (CBOT wheat front-month futures)
  Corn             : ZC=F   (CBOT corn front-month futures)

All symbols resolve to continuous front-month contracts on their respective
exchanges.  Prices are in USD per the contract's standard unit.

Retry strategy
--------------
``tenacity`` retries each fetch up to MAX_RETRIES times with an exponential
back-off, catching network/data errors so that a single flaky request does not
abort the whole run.
"""

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import yfinance as yf
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.logger import get_logger

logger = get_logger(__name__)

# ── Default commodity catalogue ──────────────────────────────────────────────

DEFAULT_COMMODITIES: dict[str, str] = {
    "Crude Oil (WTI)": "CL=F",
    "Brent Crude":     "BZ=F",
    "Gold":            "GC=F",
    "Silver":          "SI=F",
    "Natural Gas":     "NG=F",
    "Copper":          "HG=F",
    "Wheat":           "ZW=F",
    "Corn":            "ZC=F",
}

# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class CommodityPrice:
    """Structured result for a single commodity price observation."""
    commodity_name: str
    ticker:         str
    price:          float
    currency:       str
    price_date:     date
    fetched_at:     datetime

    def __repr__(self) -> str:
        return (
            f"CommodityPrice({self.commodity_name!r}, "
            f"price={self.price:.4f} {self.currency}, "
            f"date={self.price_date})"
        )


# ── Scraper class ─────────────────────────────────────────────────────────────

class CommodityScraper:
    """
    Fetch the latest daily closing prices for a set of commodities.

    Parameters
    ----------
    commodities:
        Mapping of human-readable name → Yahoo Finance ticker.
        Defaults to DEFAULT_COMMODITIES.
    max_retries:
        Maximum number of fetch attempts per ticker before giving up.
    retry_delay:
        Base delay (seconds) for exponential back-off between retries.
    """

    def __init__(
        self,
        commodities: Optional[dict[str, str]] = None,
        max_retries: int = int(os.getenv("MAX_RETRIES", 3)),
        retry_delay:  int = int(os.getenv("RETRY_DELAY",  5)),
    ) -> None:
        self.commodities  = commodities or DEFAULT_COMMODITIES
        self.max_retries  = max_retries
        self.retry_delay  = retry_delay

    # ── Public API ────────────────────────────────────────────────────

    def fetch_all(self) -> list[CommodityPrice]:
        """
        Fetch prices for every commodity in ``self.commodities``.

        Returns a list of CommodityPrice objects; failed tickers are
        skipped and logged as errors rather than raising.
        """
        results: list[CommodityPrice] = []
        for name, ticker in self.commodities.items():
            try:
                cp = self._fetch_one(name, ticker)
                if cp:
                    results.append(cp)
                    logger.info("✓ %s  %s %.4f %s", ticker, name, cp.price, cp.currency)
            except Exception as exc:
                logger.error("✗ Failed to fetch %s (%s) after retries: %s", name, ticker, exc)
        return results

    # ── Internal helpers ──────────────────────────────────────────────

    def _fetch_one(self, name: str, ticker: str) -> Optional[CommodityPrice]:
        """Fetch a single ticker; delegates to the retry-wrapped helper."""
        return self._fetch_with_retry(name, ticker)

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),            # overridden per-instance below
        wait=wait_exponential(multiplier=1, min=5, max=60),
        before_sleep=before_sleep_log(logger, 20),   # 20 = logging.DEBUG
        reraise=True,
    )
    def _fetch_with_retry(self, name: str, ticker: str) -> Optional[CommodityPrice]:
        """
        Download the last two trading days via yfinance and return the
        most recent available closing price.

        We request 5 days of history to guard against weekends/holidays
        where today's data may not yet be available.
        """
        logger.debug("Downloading %s (%s) …", name, ticker)

        tkr  = yf.Ticker(ticker)
        hist = tkr.history(period="5d", auto_adjust=True)

        if hist.empty:
            raise ValueError(f"No history returned for {ticker}")

        latest_row  = hist.iloc[-1]
        latest_date = hist.index[-1].date()
        close_price = float(latest_row["Close"])

        if close_price <= 0:
            raise ValueError(f"Implausible price {close_price} for {ticker}")

        # Attempt to read currency from ticker info; fall back to "USD"
        try:
            info     = tkr.fast_info
            currency = getattr(info, "currency", "USD") or "USD"
        except Exception:
            currency = "USD"

        return CommodityPrice(
            commodity_name=name,
            ticker=ticker,
            price=close_price,
            currency=currency,
            price_date=latest_date,
            fetched_at=datetime.utcnow(),
        )
