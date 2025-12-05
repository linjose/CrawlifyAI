# coffeemap
自用地圖
---

 **pipeline** 可直接執行的腳本與說明，包含：

* 執行前注意事項（合規與風險提示）
* 必要套件與安裝指令
* `config.json` 範本（放 API key 與參數）
* `scraper.py`：Selenium 抓取公開社團貼文（文字、時間、圖片 URL、permalink、post_id）
* `pipeline.py`：NLP 抽取店名/地址、OCR（圖片內文字）、Geocoding（Google / Nominatim fallback）、tag/attrs 推論、產出 GeoJSON
* 執行流程範例與輸出格式說明
* 後續：人工覆核建議（CSV 檢視 + 快速修改流程）

請將 `config.json` 填好（包含 Google Maps API key ）
安裝套件：執行 `scraper.py` 然後 `pipeline.py` 就能得到 GeoJSON 與圖檔資料夾。

---

### 1) 重要合規 & 使用提醒

* 抓取**FB公開社團**：
  * 僅抓取公開貼文（不登入帳號或不爬取會員個資）。
  * 維持低頻率、間隔存取（腳本內已加 sleep + jitter）。
  * 不嘗試規避或偽裝為正常用戶（例如不要刻意隱藏 automation 標誌）。
  * 若要對外公開或商用，請取得社團管理員同意或標示來源。
* Facebook 的前端結構會變動，上述腳本可能需調整 XPath 或 CSS Selector。腳本內都有註解與容錯。



### 2) 必要套件（在終端機執行）

```bash
python -m pip install selenium webdriver-manager requests beautifulsoup4 lxml pillow pytesseract pytz python-dateutil tqdm pandas
# 若使用 spaCy 的話（可選）
python -m pip install spacy
# 若要用 Google client libs（非必須）
python -m pip install googlemaps
```

另外若要做圖片 OCR，需先安裝 tesseract 引擎：
* Ubuntu：`sudo apt-get install tesseract-ocr`



### 3) `config.json`（範本） — 建一個在同目錄的檔案
`google_api_key` 可留空（會自動 fallback 到 Nominatim）。`cutoff_days` 預設為 3 年。



### 4) `scraper.py` — Selenium 抓取（文字、時間、圖片 URL、permalink、post_id）
* 無登入模式抓取公開社團內容（role="article" 篩選）。
* 會盡可能解析 `post_id`、`permalink`、`datetime`、`text` 與 `images`。
* 自動停止條件：若碰到比 cutoff 更舊的貼文就停止（你的 cutoff=3 年）。
* 會把圖片下載到 `output/images`。
* 注意：Facebook DOM 可能變動，必要時需更新 selector / 正則。



### 5) `pipeline.py` — 抽取店名 / 地址 / OCR / Geocode / Tag 推論 → 輸出 GeoJSON
* `extract_name`、`extract_address`：使用簡單 regex 與 heuristics 抽店名與地址（針對 B 類多文字情況）。
* `ocr_image`：若貼文只有照片截圖（C 情況），會對下載的圖做 Tesseract OCR，嘗試抽出店名/地址。
* `geocode`：會先呼叫 Google Geocoding（若你填 API key），否則用 OpenStreetMap Nominatim 作 fallback（記得在 `config.json` 填 email）。
* `infer_tags_attrs`：基於你同意的分類字典（我先放示例詞），會推論 `attrs` 與 `tags`。你可擴充 `TAG_KEYWORDS`。
* 會輸出兩個檔案：`coffee_geo.json`（GeoJSON）與 `review_candidates.csv`（人工覆核用）。



### 6) 執行順序

1. 編輯 `config.json`，填入 `group_url` 與 `google_api_key`與 `nominatim_email`。
2. `python scraper.py` → 會產生 `output/posts_with_images.json` 與 `output/images/*`。
3. `python pipeline.py` → 會產生 `output/coffee_geo.json` 與 `output/review_candidates.csv`。
4. 打開 `review_candidates.csv`，檢查每筆 `address_candidate` / `thumb` / `name`。對 `no_location` 的項目可以人工在 CSV 裡補地址或用小工具修正，然後重新 run `pipeline.py`（或寫一個更新腳本合併人工修正）。



### 7) 人工覆核建議
* `review_candidates.csv` 欄位：`id,name,address_candidate,coords,thumb,post`
* 你可在 Excel / Google Sheets 打開，用 `thumb` 路徑查看圖檔（或我可幫你做一個簡單 HTML 頁面把每列做成可點選的檢視器）
* 建議覆核欄位：`confirm_name`,`confirm_address`,`confirm_coords`,`final_tags`，覆核完後把 CSV 備回 `output/review_confirmed.csv`，我們再寫一個小 script 把確認檔案合併回 GeoJSON。
