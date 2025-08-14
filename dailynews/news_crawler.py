import os
import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Index, func
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert
from sqlalchemy.orm import declarative_base, sessionmaker

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# --------------------------
# Config & Logging
# --------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("news_crawler")

BASE_URL = "https://www.channelnewsasia.com"
SECTION_URL = "https://www.channelnewsasia.com/international"
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; News-Crawler/1.0; +https://example.com/bot)")
TIMEZONE = os.getenv("LOCAL_TZ", "Asia/Taipei")  # 「當日」以台北時區為準

# PostgreSQL connection string, e.g.:
# postgresql+psycopg2://user:password@host:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Missing env DATABASE_URL (e.g., postgresql+psycopg2://user:pass@host:5432/dbname)")

# --------------------------
# Database Model
# --------------------------

Base = declarative_base()

class Article(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text)
    author = Column(String)
    section = Column(String)
    published_at = Column(DateTime(timezone=True), index=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    content = Column(Text)
    metadata = Column("metadata", JSONB)  # JSON-LD (raw) & other details

Index("idx_news_articles_published_at", Article.published_at)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base.metadata.create_all(engine)

# --------------------------
# HTTP Session with retry
# --------------------------

def build_http_session():
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

http = build_http_session()

# --------------------------
# Utilities
# --------------------------

def is_article_url(url: str) -> bool:
    "Heuristics to filter News article-like URLs (we'll validate via JSON-LD later)."
    try:
        u = urlparse(url)
        if not u.netloc:
            return False
        if "channelnewsasia.com" not in u.netloc:
            return False
        excluded = ("/videos", "/watch", "/listen", "/podcasts", "/live", "/weather", "/advertise", "/newsletter")
        return not any(part in u.path for part in excluded)
    except Exception:
        return False

def absolutize(href: str, base: str = BASE_URL) -> str:
    return urljoin(base, href)

def parse_jsonld(soup: BeautifulSoup):
    "Return the first JSON-LD dict for Article/NewsArticle if available."
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            payload = tag.string or ""
            data = json.loads(payload)
        except Exception:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if isinstance(node, dict):
                t = node.get("@type")
                types = set(t if isinstance(t, list) else [t])
                if "NewsArticle" in types or "Article" in types:
                    return node
    return None

def parse_article(url: str):
    "Fetch and parse an article, return dict or None if not an article or not today."
    try:
        r = http.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        logger.warning("Fetch article failed: %s (%s)", url, e)
        return None

    soup = BeautifulSoup(r.text, "lxml")
    jsonld = parse_jsonld(soup)

    title = None
    summary = None
    author = None
    section = None
    published_at = None
    content = None

    if jsonld:
        title = jsonld.get("headline") or jsonld.get("name")
        summary = jsonld.get("description")
        # author may be dict or list
        author_data = jsonld.get("author")
        if isinstance(author_data, dict):
            author = author_data.get("name")
        elif isinstance(author_data, list):
            names = []
            for a in author_data:
                if isinstance(a, dict) and a.get("name"):
                    names.append(a["name"])
                elif isinstance(a, str):
                    names.append(a)
            if names:
                author = ", ".join(names)
        section = jsonld.get("articleSection")

        dt_str = jsonld.get("datePublished") or jsonld.get("dateCreated")
        if dt_str:
            try:
                dt = dateparser.parse(dt_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                published_at = dt
            except Exception:
                published_at = None

        content = jsonld.get("articleBody")

    # HTML fallbacks
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]
    if not summary:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            summary = og_desc["content"]
    if not section:
        bc = soup.select_one('[data-testid="breadcrumb"]') or soup.select_one("nav.breadcrumb")
        if bc:
            section = bc.get_text(" ", strip=True)
    if not content:
        paras = []
        for sel in ['div.text-long p', 'article p', 'div.c-article-content p']:
            for p in soup.select(sel):
                txt = p.get_text(" ", strip=True)
                if txt:
                    paras.append(txt)
            if paras:
                break
        if paras:
            content = "\\n\\n".join(paras)

    if not title:
        logger.debug("Skip (no title): %s", url)
        return None

    # Only today's news (Asia/Taipei by default)
    local_tz = ZoneInfo(TIMEZONE)
    today_local = datetime.now(tz=local_tz).date()
    if published_at is None:
        logger.debug("Skip (no published_at): %s", url)
        return None
    published_local_date = published_at.astimezone(local_tz).date()
    if published_local_date != today_local:
        logger.debug("Skip (not today): %s pub=%s local=%s", url, published_at.isoformat(), published_local_date)
        return None

    return {
        "url": url,
        "title": title.strip() if title else None,
        "summary": summary,
        "author": author,
        "section": section,
        "published_at": published_at,
        "content": content,
        "metadata": jsonld,
    }

def fetch_listing_links():
    "Fetch International page and collect candidate article URLs (absolute)."
    try:
        resp = http.get(SECTION_URL, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to fetch listing: %s", e)
        return set()

    soup = BeautifulSoup(resp.text, "lxml")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        abs_url = absolutize(href, base=BASE_URL)
        if is_article_url(abs_url):
            links.add(abs_url)

    logger.info("Collected %d candidate links from listing", len(links))
    return links

def upsert_articles(records):
    if not records:
        return 0
    with SessionLocal() as session:
        stmt = pg_insert(Article).values(records)
        stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
        result = session.execute(stmt)
        session.commit()
        # result.rowcount may be None depending on driver; safely handle
        return result.rowcount or 0

def run_once():
    logger.info("Starting scrape run...")
    links = fetch_listing_links()
    saved = 0
    for url in sorted(links):
        data = parse_article(url)
        if not data:
            continue
        saved += upsert_articles([data])
        logger.info("Saved: %s", data["title"])
    logger.info("Run complete. Inserted %d new articles.", saved)

# --------------------------
# Entrypoint & Scheduler
# --------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="NEWS International scraper (every 3 hours).")
    parser.add_argument("--run-once", action="store_true", help="Run a single scrape immediately and exit.")
    parser.add_argument("--interval-hours", type=int, default=3, help="Interval hours between runs (default: 3).")
    args = parser.parse_args()

    if args.run_once:
        run_once()
        return

    logger.info("Starting scheduler: every %s hours", args.interval_hours)
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(run_once, trigger=IntervalTrigger(hours=args.interval_hours, start_date=datetime.now()))
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")

if __name__ == "__main__":
    main()
