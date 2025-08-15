# dailynews
To Crawl the news website every three hours, only accessing the news of the day, without duplicate news, and store them in PostgreSQL.

## requests
 - beautifulsoup4
 - lxml
 - SQLAlchemy>=2.0
 - psycopg2-binary
 - python-dateutil
 - apscheduler
 - tzdata

## env.example
```
# Copy this to .env and fill values, then export with: source .env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
# Optional: customize timezone for "today" check
LOCAL_TZ=Asia/Taipei
# Optional: custom User-Agent
USER_AGENT=MyCNAcrawler/1.0 (+https://yourdomain.example/crawler)
# Optional: logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```
