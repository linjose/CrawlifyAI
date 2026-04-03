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

# 

撰寫一支定期執行的 Python 爬蟲程式，通常會結合 **網頁請求**、**資料解析** 與 **排程套件** 這三個核心功能。

以下為您示範如何使用 `requests` 來抓取網頁，使用 `BeautifulSoup` 解析 HTML，並利用 `schedule` 套件來達成「定期執行」的目的。

### 1. 安裝必要套件

在開始撰寫程式前，請先確保您的環境已安裝以下套件。請在終端機（Terminal）或命令提示字元中輸入以下指令：

```bash
pip install requests beautifulsoup4 schedule
```

---

### 2. 完整 Python 爬蟲範例程式碼

這是一支完整的範例程式。為了方便說明，這裡使用了一個假設的新聞網站結構。**在實際應用時，您必須將 `url` 與 `soup.find_all(...)` 替換為目標新聞網站真實的網址與 HTML 標籤結構。**

---

### 3. 程式碼重點解析

* **`User-Agent` (使用者代理)**：許多新聞網站會有反爬蟲機制。在 `headers` 加上瀏覽器的 User-Agent，可以讓程式看起來像是正常人類在瀏覽網頁，降低被阻擋的機率。
* **`BeautifulSoup` 解析**：這是抓取資料的核心。網頁的架構常常變動，您必須透過瀏覽器的「開發者工具（F12）」去觀察該新聞網把標題和連結包在什麼 HTML 標籤內（例如 `<div class="story-title">` 或 `<h3>`），並據此修改 `soup.find_all(...)` 的參數。
* **`schedule` 排程**：它的語法非常口語化（例如 `schedule.every(1).hours.do(job)`）。底下的 `while True` 迴圈是必須的，它會讓 Python 程式持續掛在背景執行，並透過 `time.sleep(1)` 避免佔用過多電腦效能。

### 4. 實務上的注意事項與建議

* **確認 `robots.txt`**：在爬取任何新聞網之前，建議先在目標網址後方加上 `/robots.txt`（例如 `https://example.com/robots.txt`），確認網站是否允許爬蟲抓取該路徑的資料。
* **控制請求頻率**：不要設定過於頻繁的排程（例如每秒抓一次）。新聞網站更新頻率有限，過度頻繁的請求不僅會對對方伺服器造成負擔，也極有可能導致您的 IP 被封鎖。一般建議設定每幾十分鐘或每小時抓取一次即可。
* **動態載入的網頁**：如果新聞網站是使用 JavaScript 動態載入資料（例如無限向下滾動的頁面），單純使用 `requests` 可能會抓不到內容。遇到這種情況，您可能需要改用 `Selenium` 或 `Playwright` 這種可以模擬瀏覽器行為的套件，或是去尋找網頁背後真正呼叫的 API 網址。
