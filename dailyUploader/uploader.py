import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from github import Github
from github.GithubException import UnknownObjectException

# ================= 參數設定區 =================
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
GITHUB_REPO = "github_username/repo_name"  # 格式為 帳號/儲存庫名稱
FILE_PATH_IN_REPO = f"data_export/data_{ (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d') }.json"

# SQL 查詢 (請依照實際的資料表與日期欄位修改)
TABLE_NAME = "your_table_name"
DATE_COLUMN = "created_at"
# ==============================================

def fetch_data_from_db():
    """從資料庫撈取 7 天前的資料"""
    # 計算 7 天前的日期 (格式: YYYY-MM-DD)
    target_date = (datetime.now() - timedelta(days=7)).date()
    print(f"準備撈取日期為 {target_date} 的資料...")

    try:
        # 建立連線
        conn = psycopg2.connect(**DB_CONFIG)
        # 使用 RealDictCursor 讓回傳的資料直接是 Dict 格式，方便轉 JSON
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 執行查詢 (使用 DATE() 確保只比對日期部分)
        query = f"SELECT * FROM {TABLE_NAME} WHERE DATE({DATE_COLUMN}) = %s;"
        cursor.execute(query, (target_date,))
        records = cursor.fetchall()
        
        return records, target_date

    except Exception as e:
        print(f"資料庫讀取失敗: {e}")
        return None, None
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

def upload_to_github(json_data, target_date):
    """將 JSON 字串寫入 GitHub Repo"""
    print("準備上傳至 GitHub...")
    g = Github(GITHUB_TOKEN)
    
    try:
        repo = g.get_repo(GITHUB_REPO)
        commit_message = f"Auto-upload: DB data backup for {target_date}"
        
        try:
            # 嘗試取得檔案 (如果檔案已經存在，則進行更新)
            contents = repo.get_contents(FILE_PATH_IN_REPO)
            repo.update_file(
                path=contents.path, 
                message=commit_message, 
                content=json_data, 
                sha=contents.sha
            )
            print(f"檔案已存在，更新成功！路徑: {FILE_PATH_IN_REPO}")
            
        except UnknownObjectException:
            # 檔案不存在，直接建立新檔案
            repo.create_file(
                path=FILE_PATH_IN_REPO, 
                message=commit_message, 
                content=json_data
            )
            print(f"新檔案建立成功！路徑: {FILE_PATH_IN_REPO}")

    except Exception as e:
        print(f"GitHub 上傳失敗: {e}")

def main():
    # 1. 撈取資料
    records, target_date = fetch_data_from_db()
    
    if not records:
        print("沒有找到符合條件的資料，或資料庫連線失敗。")
        return

    # 2. 轉換為 JSON 格式
    # default=str 是為了處理 datetime/date 等無法直接被 json serialize 的物件
    json_data = json.dumps(records, default=str, ensure_ascii=False, indent=4)
    
    # 3. 寫入 GitHub
    upload_to_github(json_data, target_date)

if __name__ == "__main__":
    main()
