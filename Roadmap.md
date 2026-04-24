# 📊 Data Crawler Roadmap

This repository started as a collection of daily crawlers (commodities, crypto, FX, news, etc.).  
The next goal is to evolve from **data collection → data insight → data product**.

---

## 🧭 Phase 1: Enhance Existing Crawlers (Data → Insight)

Upgrade current crawlers by adding analysis and value extraction.

### 🔹 Financial Data Analysis
- Price anomaly detection (e.g. Z-score, moving average)
- Cross-market correlation (Crypto vs Commodities vs FX)
- Volatility tracking

### 🔹 News Intelligence
- Sentiment analysis on news
- Topic classification (e.g. finance, politics, tech)
- Correlate news sentiment with market movements

👉 Goal: Transform raw data into meaningful signals

---

## 🌏 Phase 2: Local & Lifestyle Data Expansion

Introduce Taiwan/local datasets to build more practical applications.

### 🔹 Potential Data Sources
- Real estate transaction data
- Rental listings (e.g. 591)
- Restaurant reviews / ratings
- Weather & air quality
- Fuel / electricity prices

### 🔹 Example Projects
- Taipei rental price heatmap
- Coffee shop price vs rating analysis (extend `coffeemap`)
- Cost of living tracker

👉 Goal: Build relatable and user-centric datasets

---

## ⚖️ Phase 3: Structured Knowledge Systems

Extend structured datasets like judicial data into deeper analysis.

### 🔹 Legal Data (judbp)
- Case classification (fraud, labor dispute, etc.)
- Sentencing statistics
- Keyword-based legal search

👉 Goal: Build high-value, structured datasets with analytical depth

---

## 🛒 Phase 4: Price Tracking & Monitoring System

Create practical tools that can evolve into products.

### 🔹 Targets
- E-commerce platforms (PChome, momo, Shopee)
- Game platforms (Steam)
- International platforms (Amazon)

### 🔹 Features
- Historical price tracking
- Price drop alerts (Telegram / Discord bot)
- Trend visualization

👉 Goal: Turn crawlers into useful services

---

## 🎮 Phase 5: Trend & Entertainment Data

Build fun, dynamic datasets for exploration and visualization.

### 🔹 Ideas
- Steam trending games
- YouTube trending videos
- Netflix / anime rankings

### 🔹 Applications
- Trend change tracking
- Viral growth analysis
- Popularity prediction

👉 Goal: Make data exploration engaging and visual

---

## 🤖 Phase 6: Advanced Data Engineering

Upgrade the system architecture for scalability and real-time processing.

### 🔹 Real-Time Systems
- WebSocket-based data ingestion (crypto, stock prices)
- Live dashboards

### 🔹 Data Pipeline
- Task orchestration (Airflow / Prefect)
- Streaming systems (Kafka)

### 🔹 AI Integration
- News summarization (LLM)
- Sentiment analysis automation
- Daily report generation

👉 Goal: Move toward production-grade data systems

---

## 🚀 Flagship Project Ideas

High-impact projects combining multiple components:

1. **News + Market Intelligence System**
   - News sentiment → market movement analysis

2. **Taiwan Rental & Housing Analytics Platform**
   - Rental trends, heatmaps, affordability metrics

3. **Smart Price Tracker with Alerts**
   - Multi-platform price monitoring + notification system

---

## 📌 Long-Term Vision

- Build a unified data platform
- Provide APIs for all datasets
- Develop dashboards for visualization
- Turn selected modules into standalone products

---

## 🛠️ Tech Stack (Planned)

- Crawling: Python (requests, Selenium, Playwright)
- Data Processing: Pandas / Polars
- Storage: PostgreSQL / MongoDB
- Scheduling: Cron / Airflow
- Backend: FastAPI
- Visualization: Streamlit / Frontend framework
- Notification: Telegram Bot API

---

## 📈 Progress Strategy

- Start from existing crawlers
- Add analysis layer
- Build APIs
- Add visualization
- Integrate into unified system

---
