# =============================================================================
# Dockerfile — Commodity Price Scraper
# =============================================================================
# Build:   docker build -t commodity-scraper .
# Run:     docker run --env-file .env commodity-scraper
# Schedule:docker run --env-file .env commodity-scraper --schedule
# =============================================================================

FROM python:3.11-slim

# ── System dependencies (psycopg2 needs libpq) ─────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ───────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies (cached layer) ─────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ──────────────────────────────────────────────────────
COPY . .

# Create logs directory
RUN mkdir -p logs

# ── Default command ─────────────────────────────────────────────────────────
# Override with: docker run ... --schedule --schedule-time 18:00
ENTRYPOINT ["python", "main.py"]
CMD []
