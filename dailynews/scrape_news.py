import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime

def scrape_news():
    """爬取新聞網站的核心函式"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 啟動新聞爬蟲任務...")
    
    # 1. 設定目標網址 (請替換為實際想爬取的新聞網站)
    url = "https://example-news-website.com" 
    
    # 2. 設定 User-Agent 偽裝成瀏覽器，避免被網站直接阻擋
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # 發送 GET 請求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # 若發生 4xx 或 5xx 錯誤會拋出異常
        
        # 3. 解析 HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 4. 尋找新聞標題與連結
        # ⚠️ 注意：這裡的 "h2" 和 class_="news-title" 只是範例！
        # 您需要對目標網頁按右鍵「檢查(Inspect)」，找出真實的 HTML 標籤與 class。
        news_items = soup.find_all("h2", class_="news-title")
        
        if not news_items:
            print("找不到新聞資料，請確認網頁結構是否已改變或標籤設定錯誤。")
            return

        print("=== 最新新聞摘要 ===")
        # 只取前 5 筆作為示範
        for item in news_items[:5]:
            title = item.text.strip()
            # 尋找 <h2> 標籤底下的 <a> 標籤來取得超連結
            a_tag = item.find("a")
            link = a_tag["href"] if a_tag and "href" in a_tag.attrs else "無連結"
            
            # 若連結是相對路徑，可以自行補上主網域
            if link.startswith("/"):
                link = "https://example-news-website.com" + link

            print(f"標題: {title}")
            print(f"連結: {link}")
            print("-" * 30)
            
    except requests.exceptions.RequestException as e:
        print(f"網路請求發生錯誤: {e}")
    except Exception as e:
        print(f"程式發生未預期的錯誤: {e}")

# ==========================================
# 5. 設定排程機制
# ==========================================

# 範例 A：每小時執行一次
schedule.every(1).hours.do(scrape_news)

# 範例 B：每天早上 8 點執行一次 (可取消註解測試)
# schedule.every().day.at("08:00").do(scrape_news)

# 範例 C：每 10 秒執行一次 (適合剛開始測試程式碼時使用)
# schedule.every(10).seconds.do(scrape_news)

print("✅ 排程爬蟲已啟動！請保持程式運行（按 Ctrl+C 可結束程式）...")

# 讓程式保持運行，並不斷檢查是否有到期的排程任務
while True:
    schedule.run_pending()
    time.sleep(1) # 暫停 1 秒避免過度消耗 CPU 資源
