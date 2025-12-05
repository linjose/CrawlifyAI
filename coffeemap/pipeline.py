# pipeline.py
import os, json, re, time, random
from datetime import datetime
from collections import defaultdict
import requests
from PIL import Image
import pytesseract
from urllib.parse import urlencode
from tqdm import tqdm
import pandas as pd

cfg = json.load(open("config.json", "r", encoding="utf-8"))
OUT_DIR = cfg.get("output_dir", "output")
IMAGES_DIR = os.path.join(OUT_DIR, "images")
RAW_PATH = os.path.join(OUT_DIR, "posts_with_images.json")
GEOJSON_OUT = os.path.join(OUT_DIR, "coffee_geo.json")
CUTOFF_DAYS = int(cfg.get("cutoff_days", 365*3))

# --- helper: simple address regex for Taiwan (very heuristic) ---
ADDRESS_PATTERN = re.compile(r'((台灣|台北市|台中市|台南市|高雄市|新北市|桃園市|台中|台北|高雄|新北|南投縣|苗栗縣|台南縣|屏東縣|宜蘭縣|基隆市|彰化縣|嘉義市|嘉義縣|雲林縣|新竹市|新竹縣).{2,80}?\d{1,4}號?)', re.I)

# example store keywords for tags/attrs - you can expand this list
TAG_KEYWORDS = {
    "breakfast": ["早午餐","brunch","早餐","morning"],
    "meal": ["主餐","午餐","晚餐","套餐","義大利麵","飯","排餐"],
    "socket": ["插座","充電","插頭","插座友善"],
    "pet": ["寵物","毛孩","可帶狗","寵物友善"],
    "roastery": ["烘豆","烘焙","自家烘焙","roastery"],
    "dessert": ["甜點","蛋糕","甜品"],
    "night_open": ["深夜","營業到","凌晨","夜貓"]
}

def ocr_image(img_path):
    try:
        full = os.path.join(OUT_DIR, img_path)
        if not os.path.exists(full):
            return ""
        txt = pytesseract.image_to_string(Image.open(full), lang="chi_sim+eng")
        return txt
    except Exception as e:
        return ""

def extract_address(text, images_text=""):
    # try regex first
    addr_candidates = []
    for m in ADDRESS_PATTERN.findall(text):
        addr_candidates.append(m[0])
    # from OCR text
    for m in ADDRESS_PATTERN.findall(images_text):
        addr_candidates.append(m[0])
    # dedupe
    if addr_candidates:
        return addr_candidates[0]
    return None

def extract_name(text):
    # heuristics:
    # - common pattern: 「店名」 or 『店名』 or 名稱：xxx or 店名：xxx
    m = re.search(r'[「『](.+?)[」』]', text)
    if m:
        return m.group(1).strip()
    m = re.search(r'店名[:：\s]*([^\n,，。]+)', text)
    if m:
        return m.group(1).strip()
    # fallback: first line (short)
    first_line = text.splitlines()[0].strip()
    if 2 <= len(first_line) <= 50:
        # avoid long sentences
        return first_line
    return None

def infer_tags_attrs(text, images_text=""):
    tags = set()
    attrs = {
        "breakfast": None,
        "meal": None,
        "socket": None,
        "seat": None,
        "pet": None,
        "wifi": None,
        "roastery": None,
        "dessert": None,
        "night_open": None
    }
    full_text = (text + "\n" + images_text).lower()
    for k, kws in TAG_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in full_text:
                if k in ["breakfast","meal","socket","pet","roastery","dessert","night_open"]:
                    attrs[k] = True
                else:
                    tags.add(k)
    # seat inference
    if any(w in full_text for w in ["座位少","座位不多","外帶為主","外帶"]):
        attrs["seat"] = "少"
    elif any(w in full_text for w in ["座位多","座位寬敞","座位很多","空間大"]):
        attrs["seat"] = "多"
    elif any(w in full_text for w in ["座位","座"]) :
        attrs["seat"] = "中"
    return list(tags), attrs

def geocode_address_google(address, api_key):
    endpoint = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}
    r = requests.get(endpoint, params=params, timeout=10)
    j = r.json()
    if j.get("status") == "OK":
        loc = j["results"][0]["geometry"]["location"]
        return loc["lng"], loc["lat"], j["results"][0].get("formatted_address")
    return None

def geocode_nominatim(address, email):
    endpoint = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "addressdetails": 1, "limit": 1, "email": email}
    r = requests.get(endpoint, params=params, headers={"User-Agent":"fb-scraper/1.0"}, timeout=10)
    j = r.json()
    if j:
        return float(j[0]["lon"]), float(j[0]["lat"]), j[0].get("display_name")
    return None

def run():
    raw = json.load(open(RAW_PATH, "r", encoding="utf-8"))
    features = []
    id_counter = 1000
    results_for_review = []

    for p in tqdm(raw):
        text = p.get("text","")
        dt = p.get("datetime")
        if dt is None:
            # skip if no time
            pass

        # OCR images text aggregation (for cases where screenshot holds address)
        images_text = ""
        for img in p.get("saved_images", []):
            images_text += ocr_image(img) + "\n"

        name = extract_name(text + "\n" + images_text)
        address = extract_address(text, images_text)

        # if no address, leave None (we decided behavior 2 -> mark no_location)
        coords = None
        formatted_addr = None
        if address:
            # try google first
            if cfg.get("use_google_geocode") and cfg.get("google_api_key"):
                try:
                    out = geocode_address_google(address, cfg["google_api_key"])
                    if out:
                        coords = [out[0], out[1]]
                        formatted_addr = out[2]
                except Exception:
                    coords = None
            # fallback to nominatim
            if not coords:
                try:
                    out = geocode_nominatim(address, cfg.get("nominatim_email", ""))
                    if out:
                        coords = [out[0], out[1]]
                        formatted_addr = out[2]
                except Exception:
                    coords = None
            time.sleep(1 + random.random()*0.5)  # rate limit friendly

        tags, attrs = infer_tags_attrs(text, images_text)

        # ensure seat key exists
        if attrs.get("seat") is None:
            attrs["seat"] = None

        feat = {
            "type":"Feature",
            "geometry": {"type":"Point", "coordinates": coords if coords else [0,0]},
            "properties": {
                "id": id_counter,
                "name": name if name else None,
                "intro": (text[:400] if text else None),
                "address": formatted_addr if formatted_addr else (address if address else None),
                "closed_day": None,
                "tags": tags,
                "thumb": p.get("saved_images",[None])[0] if p.get("saved_images") else None,
                "attrs": attrs,
                "source": p.get("permalink"),
                "post_datetime": dt
            }
        }
        id_counter += 1

        # mark no_location if no coords found but there is some hint
        if not coords:
            feat["properties"]["no_location"] = True

        features.append(feat)
        # add minimal row for review
        results_for_review.append({
            "id": feat["properties"]["id"],
            "name": feat["properties"]["name"],
            "address_candidate": feat["properties"]["address"],
            "coords": feat["geometry"]["coordinates"],
            "thumb": feat["properties"]["thumb"],
            "post": feat["properties"]["source"]
        })

    # write geojson
    geo = {"type":"FeatureCollection", "features": features}
    with open(GEOJSON_OUT, "w", encoding="utf-8") as f:
        json.dump(geo, f, ensure_ascii=False, indent=2)

    # write review CSV for manual verification
    df = pd.DataFrame(results_for_review)
    review_csv = os.path.join(OUT_DIR, "review_candidates.csv")
    df.to_csv(review_csv, index=False, encoding="utf-8-sig")

    print("Done. GeoJSON:", GEOJSON_OUT, "Review CSV:", review_csv)

if __name__ == "__main__":
    run()
