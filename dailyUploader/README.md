# Uploader to GitHub (with JSON)

## ✨ 功能特色

* **自動化日期計算**：自動推算執行當下的前 7 天（T-7），精準撈取目標資料。
* **無縫 JSON 轉換**：自動處理關聯式資料庫中常見的日期與時間物件，確保 JSON 序列化不報錯。
* **智慧化檔案管理**：上傳 GitHub 時，若檔案不存在則自動建立；若檔案已存在則自動進行 Commit 更新。
* **支援 PostgreSQL**：使用 `psycopg2` 與 `RealDictCursor`，確保取出的資料結構清晰易讀。

## 🛠️ 事前準備

在執行此程式之前，請確保你具備以下條件：

1. **Python 環境**：建議使用 Python 3.7 或以上版本。
2. **PostgreSQL 資料庫**：確認資料庫可正常連線，且具有讀取目標資料表的權限。
3. **GitHub Personal Access Token (PAT)**：
   * 請至 GitHub 的 [Developer settings -> Personal access tokens](https://github.com/settings/tokens) 申請。
   * Token 必須包含 **`repo`** 權限，才能寫入資料至你的儲存庫。

## 📦 安裝套件

請在專案目錄下執行以下指令，安裝必備的 Python 套件：

```bash
pip install psycopg2-binary PyGithub
```
*(註：若在正式環境中，建議將上述套件寫入 `requirements.txt` 中)*

## ⚙️ 參數設定

請開啟 `main.py`（或你的 Python 程式檔名），找到 `==== 參數設定區 ====`，並替換為你實際的環境變數：

```python
# 資料庫連線設定
DB_CONFIG = {
    "dbname": "your_database_name",
    "user": "your_username",
    "password": "your_password",
    "host": "localhost",
    "port": "5432"
}

# GitHub 設定
GITHUB_TOKEN = "your_github_personal_access_token"
GITHUB_REPO = "github_username/repo_name"  # 範例：'octocat/my-data-repo'

# SQL 查詢目標
TABLE_NAME = "your_table_name"
DATE_COLUMN = "created_at"  # 用於比對「7天前」的日期欄位名稱
```

> **⚠️ 安全建議**：在正式的生產環境中，強烈建議不要將帳號密碼與 GitHub Token 明碼寫入程式碼中。建議改用 `os.environ.get()` 讀取系統環境變數，或使用 `python-dotenv` 套件來管理機敏資訊。

## 🚀 使用方式

設定完成後，直接透過命令列執行該 Python 檔案：

```bash
python main.py
```

執行成功後，終端機將會輸出以下流程資訊：
1. `準備撈取日期為 YYYY-MM-DD 的資料...`
2. `準備上傳至 GitHub...`
3. `新檔案建立成功！路徑: data_export/data_YYYY-MM-DD.json`（或顯示更新成功）

## ⏰ 排程自動化 (Optional)

若希望系統每天自動幫你備份 7 天前的資料，可以將此腳本加入 Linux 的 `crontab` 排程中。

輸入 `crontab -e` 編輯排程，並加入以下設定（範例為每天凌晨 2 點自動執行）：

```bash
0 2 * * * /usr/bin/python3 /path/to/your/script/main.py >> /path/to/your/script/cron.log 2>&1
```
