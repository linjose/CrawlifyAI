# scraper.py
import os, time, json, random, re
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import requests
from dateutil import parser as dateparser
from tqdm import tqdm

# load config
import json as _json
cfg = _json.load(open("config.json", "r", encoding="utf-8"))

GROUP_URL = cfg["group_url"]
OUT_DIR = cfg.get("output_dir", "output")
os.makedirs(OUT_DIR, exist_ok=True)
IMAGES_DIR = os.path.join(OUT_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

MAX_SCROLLS = cfg.get("max_scrolls", 40)
SLEEP = cfg.get("sleep_between_scrolls", 2.5)
JITTER = cfg.get("jitter",1.5)
CUTOFF_DAYS = int(cfg.get("cutoff_days", 365*3))

cutoff_dt = datetime.now() - timedelta(days=CUTOFF_DAYS)

def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,2000")
    # don't try to hide automation (we're avoiding evasion)
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    return driver

def parse_time_from_element(el):
    # try to get datetime from time element attributes
    try:
        time_el = el.find("abbr")
        if time_el and time_el.has_attr("data-utime"):
            # older FB had data-utime
            ts = int(time_el["data-utime"])
            return datetime.fromtimestamp(ts)
        # fallback: look for datetime attr
        time_el = el.find("time")
        if time_el and time_el.has_attr("datetime"):
            return dateparser.parse(time_el["datetime"])
    except Exception:
        pass
    # last resort: return now
    return None

def download_img(url, post_id, idx):
    try:
        resp = requests.get(url, stream=True, timeout=20)
        resp.raise_for_status()
        ext = ".jpg"
        fname = f"{post_id}-{idx}{ext}"
        fpath = os.path.join(IMAGES_DIR, fname)
        with open(fpath, "wb") as f:
            for chunk in resp.iter_content(10240):
                f.write(chunk)
        return os.path.relpath(fpath, OUT_DIR)
    except Exception as e:
        print("下載圖片失敗:", e)
        return None

def get_posts(driver):
    driver.get(GROUP_URL)
    time.sleep(5 + random.random()*2)

    # scroll and collect html snapshots until cutoff or max scrolls
    posts = {}
    last_height = driver.execute_script("return document.body.scrollHeight")
    scrolls = 0
    while scrolls < MAX_SCROLLS:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SLEEP + random.random()*JITTER)
        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")

        # FB structure is complex: look for article tags or div[role='article']
        for art in soup.find_all(["article", "div"], attrs={"role":"article"}):
            try:
                # extract text
                text_el = art.find(lambda tag: tag.name in ["div","span"] and tag.get("data-ad-preview")=="message")
                if not text_el:
                    # fallback: get long text
                    text_el = art.find("div", recursive=True)
                text = text_el.get_text(separator="\n").strip() if text_el else ""

                # permalink / post id detection
                permalink = None
                post_id = None
                # find anchor with /posts/ or /permalink/
                a = art.find("a", href=True)
                if a:
                    href = a["href"]
                    if "/posts/" in href or "/permalink/" in href:
                        permalink = href
                        # try extract id
                        m = re.search(r'/posts/(\d+)', href)
                        if m:
                            post_id = m.group(1)
                # fallback: look for data-ft or data-testid attributes
                if not post_id:
                    m2 = re.search(r'"top_level_post_id":"(\d+)"', str(art))
                    if m2:
                        post_id = m2.group(1)

                # get time
                dt = parse_time_from_element(art)
                if dt and dt < cutoff_dt:
                    # we've reached older posts; stop crawling further
                    return posts

                # images
                images = []
                # look for image tags inside article
                for idx, img in enumerate(art.find_all("img")):
                    src = img.get("src")
                    if src and "scontent" in src or src:
                        images.append(src)

                # dedupe by text+permalink
                key = post_id or (text[:120] + (permalink or ""))
                if key not in posts:
                    posts[key] = {
                        "post_id": post_id,
                        "permalink": permalink,
                        "text": text,
                        "datetime": dt.isoformat() if dt else None,
                        "images": images
                    }
            except Exception as e:
                continue

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scrolls += 1
    return posts

def main():
    driver = setup_driver(headless=True)
    try:
        posts = get_posts(driver)
    finally:
        driver.quit()

    # save raw posts
    raw_path = os.path.join(OUT_DIR, "posts_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(list(posts.values()), f, ensure_ascii=False, indent=2)

    print(f"抓到 {len(posts)} 篇貼文，已儲存到 {raw_path}")

    # download images (optional)
    for p in posts.values():
        pid = p.get("post_id") or str(abs(hash(p.get("text",""))))[:12]
        saved = []
        for idx, url in enumerate(p.get("images",[])):
            rel = download_img(url, pid, idx)
            if rel:
                saved.append(rel)
        p["saved_images"] = saved

    with open(os.path.join(OUT_DIR, "posts_with_images.json"), "w", encoding="utf-8") as f:
        json.dump(list(posts.values()), f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
