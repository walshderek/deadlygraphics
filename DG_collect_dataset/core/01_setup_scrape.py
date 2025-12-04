# Script Name: core/01_setup_scrape.py
import os, sys, requests, re, concurrent.futures, utils
from io import BytesIO
from PIL import Image

def fetch_bing(query, limit):
    print(f"--> Bing Search: '{query}'")
    url = f"https://www.bing.com/images/async?q={query}&first=0&count={limit}&adlt=off"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        return re.findall(r'murl&quot;:&quot;(.*?)&quot;', requests.get(url, headers=headers).text)[:limit]
    except: return []

def dl(url, dest, idx):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code==200:
            Image.open(BytesIO(r.content)).convert("RGB").save(os.path.join(dest, f"img_{idx:04d}.jpg"), "JPEG")
            return True
    except: return False

def run(name, limit=50, gender=None):
    slug = utils.slugify(name)
    path = utils.get_project_path(slug) / utils.DIRS['scrape']
    path.mkdir(parents=True, exist_ok=True)
    print(f"--> Output: {path}")
    urls = fetch_bing(name, limit)
    if not urls: print("❌ No images."); return slug
    print(f"--> Downloading {len(urls)}...")
    with concurrent.futures.ThreadPoolExecutor(10) as ex:
        list(ex.map(lambda p: dl(p[1], str(path), p[0]), enumerate(urls)))
    utils.save_config(slug, {"name": name, "trigger": "ohwx", "gender": gender})
    return slug