import requests
import json
from datetime import date

def fetch_filename():
    url = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/EXPORT.htm?gov=&crtnm=%E5%85%A8%E9%83%A8&court=&county=&town=&proptype=C51C52&saletype=1&keyword=&saledate1=&saledate2=&minprice1=&minprice2=&saleno=&crmyy=&crmid=&crmno=&dpt=&comm_yn=&stopitem=&sec=&rrange=&area1=&area2=&debtor=&checkyn=&emptyyn=&ttitle=&sorted_column=A.CRMYY%2C+A.CRMID%2C+A.CRMNO%2C+A.SALENO%2C+A.ROWID&sorted_type=ASC&_ORDER_BY=&pageNum=1&pageSize=15"
    
    response = requests.get(url)
    if response.status_code == 200:
        with open("f.txt", "w", encoding="utf-8") as file:
            file.write(response.text)
        
        data = json.loads(response.text)
        if "data" in data and data["data"]:
            return data["data"]
        else:
            print("No filename found in response.")
            return None
    else:
        print("Failed to fetch data.")
        return None

def download_xls(filename):
    download_url = f"https://aomp109.judicial.gov.tw/judbp/wkw//WHD1A02/DOWNLOAD?fileName={filename}"
    response = requests.get(download_url)
    
    current_date = date.today()
    filename = current_date.strftime("%Y%m%d") + ".xls"
    
    if response.status_code == 200:
        with open(filename, "wb") as file:
            file.write(response.content)
        print(f"Downloaded: {filename}")
    else:
        print("Failed to download XLS file.")

if __name__ == "__main__":
    filename = fetch_filename()
    if filename:
        download_xls(filename)
