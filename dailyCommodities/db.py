"""
db.py - PostgreSQL persistence layer using SQLAlchemy 2.x + psycopg2.

Schema
------
Table: commodity_prices
  id             SERIAL PRIMARY KEY
  commodity_name VARCHAR(120)  NOT NULL
  ticker         VARCHAR(20)   NOT NULL
  price          NUMERIC(18,6) NOT NULL
  currency       VARCHAR(10)   NOT NULL DEFAULT 'USD'
  price_date     DATE          NOT NULL
  fetched_at     TIMESTAMP     NOT NULL DEFAULT now()

Unique constraint: (commodity_name, price_date) — one row per
commodity per calendar day.  Duplicate inserts are silently ignored
via INSERT … ON CONFLICT DO NOTHING.
"""

import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.crawler import CommodityPrice
from src.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


# ── ORM base & model ─────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class CommodityPriceRecord(Base):
    """ORM mapping for the commodity_prices table."""

    __tablename__ = "commodity_prices"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    commodity_name = Column(String(120), nullable=False)
    ticker         = Column(String(20),  nullable=False)
    price          = Column(Numeric(18, 6), nullable=False)
    currency       = Column(String(10),  nullable=False, default="USD")
    price_date     = Column(Date,        nullable=False)
    fetched_at     = Column(DateTime,    nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "commodity_name", "price_date",
            name="uq_commodity_price_date",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CommodityPriceRecord "
            f"name={self.commodity_name!r} "
            f"price={self.price} "
            f"date={self.price_date}>"
        )


# ── Database manager ─────────────────────────────────────────────────────────

class DatabaseManager:
    """
    Manages the SQLAlchemy engine, table creation, and data insertion.

    Connection parameters are read from environment variables (via .env):
      DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    """

    def __init__(self) -> None:
        self._engine = self._build_engine()
        self._Session = sessionmaker(bind=self._engine, expire_on_commit=False)

    # ── Lifecycle ─────────────────────────────────────────────────────

    def init_db(self) -> None:
        """Create all tables (no-op if they already exist)."""
        Base.metadata.create_all(self._engine)
        logger.info("Database tables verified / created.")

    def close(self) -> None:
        """Dispose the connection pool."""
        self._engine.dispose()
        logger.debug("Database engine disposed.")

    # ── Data operations ───────────────────────────────────────────────

    def upsert_prices(self, prices: list[CommodityPrice]) -> tuple[int, int]:
        """
        Insert commodity prices, skipping duplicates.

        Uses PostgreSQL's ``INSERT … ON CONFLICT DO NOTHING`` so that
        re-running the scraper on the same day is always safe.

        Returns
        -------
        (inserted, skipped) counts.
        """
        if not prices:
            return 0, 0

        rows = [
            {
                "commodity_name": cp.commodity_name,
                "ticker":         cp.ticker,
                "price":          cp.price,
                "currency":       cp.currency,
                "price_date":     cp.price_date,
                "fetched_at":     cp.fetched_at,
            }
            for cp in prices
        ]

        stmt = (
            pg_insert(CommodityPriceRecord)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["commodity_name", "price_date"])
        )

        with self._session() as session:
            result   = session.execute(stmt)
            inserted = result.rowcount
            session.commit()

        skipped = len(rows) - inserted
        logger.info("DB upsert: %d inserted, %d skipped (duplicate).", inserted, skipped)
        return inserted, skipped

    def get_latest_prices(self) -> list[dict]:
        """Return the most recent price row for each commodity."""
        sql = text(
            """
            SELECT DISTINCT ON (commodity_name)
                commodity_name, ticker, price::float, currency, price_date, fetched_at
            FROM commodity_prices
            ORDER BY commodity_name, price_date DESC
            """
        )
        with self._session() as session:
            rows = session.execute(sql).mappings().all()
        return [dict(r) for r in rows]

    # ── Internal helpers ──────────────────────────────────────────────

    @contextmanager
    def _session(self) -> Generator[Session, None, None]:
        """Context manager that provides a transactional session."""
        session: Session = self._Session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _build_engine():
        """Construct the SQLAlchemy engine from environment variables."""
        host     = os.getenv("DB_HOST",     "localhost")
        port     = os.getenv("DB_PORT",     "5432")
        dbname   = os.getenv("DB_NAME",     "commodities_db")
        user     = os.getenv("DB_USER",     "postgres")
        password = os.getenv("DB_PASSWORD", "")

        dsn = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        logger.debug("Connecting to %s@%s:%s/%s", user, host, port, dbname)

        engine = create_engine(
            dsn,
            pool_pre_ping=True,      # verify connections before use
            pool_size=3,
            max_overflow=5,
            echo=False,
        )
        return engine
